import cv2
import time
import os
import threading
import queue
from ultralytics import YOLO
from src.engines.ocr_engine import ShipOCR
from src.utils.report_utils import save_test_report
from src.utils.connect import get_db_connection, release_connection   # ← ĐÃ THÊM
from src.engines.speed_estimator import SpeedEstimator

class YoloTester:
    def __init__(self, model_path, input_source, output_folder,
                 conf=0.5, imgsz=640, stride=1, use_ocr=False):

        self.model_path = model_path
        self.input_source = input_source
        self.output_folder = output_folder
        self.conf = conf
        self.imgsz = imgsz
        self.stride = stride
        self.use_ocr = use_ocr
        self.stop_event = False

        video_name = os.path.basename(input_source) if isinstance(input_source, str) else "live_camera"
        self.session_id = f"{video_name}_{int(time.time())}"
        print(f">> Session ID: {self.session_id}")

        print(f">> Loading YOLO: {model_path}")
        self.model = YOLO(model_path)

        self.ocr_queue = queue.Queue()
        self.ocr_engine = None

        if use_ocr:
            try:
                self.ocr_engine = ShipOCR()
                threading.Thread(target=self.ocr_worker, daemon=True).start()
            except Exception as e:
                print(f"Lỗi Init OCR: {e}")

        self.ocr_cache = {}
        self.current_objects = {}
        self.all_confs = []

        self.class_short = {
            "fishing_boat": "F",
            "speed_boat": "S",
            "passenger": "P",
            "passenger_ship": "P",
        }

        self.speed_estimator = None

    # ==================== OCR WORKER (ĐÃ SỬA CHO POOL) ====================
    def ocr_worker(self):
        print(">> OCR Worker started...")
        while True:
            try:
                item = self.ocr_queue.get(timeout=0.5)
                track_id, crop_img, is_priority = item

                results = self.ocr_engine.ocr_image(crop_img)

                if not results:
                    self.ocr_queue.task_done()
                    continue

                best = max(results, key=lambda x: x.get("score", 0))
                text = best["text"].strip().upper()
                score = best["score"]

                if len(text) < 3:
                    self.ocr_queue.task_done()
                    continue

                print(f">> OCR Result [track_id {track_id}]: {text} ({score:.1%})")

                if track_id not in self.ocr_cache:
                    self.ocr_cache[track_id] = {"texts": [], "final": None}
                self.ocr_cache[track_id]["final"] = text

                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT ship_id FROM ship WHERE so_hieu = %s", (text,))
                        row = cursor.fetchone()

                        if row:
                            ship_id = row[0]
                        else:
                            cursor.execute("""
                                INSERT INTO ship (so_hieu, class_name, mo_ta, ngay_tao)
                                VALUES (%s, 'Unknown', %s, NOW())
                                RETURNING ship_id
                            """, (text, f"Tàu được phát hiện tự động qua OCR: {text}"))
                            ship_id = cursor.fetchone()[0]

                        cursor.execute("""
                            UPDATE shiplog 
                            SET ship_id = %s, so_hieu_ocr = %s, do_tin_cay_ocr = %s
                            WHERE track_id = %s AND session_id = %s
                        """, (ship_id, text, score, int(track_id), self.session_id))

                        conn.commit()
                    except Exception as db_e:
                        print(f"❌ DB Error: {db_e}")
                        conn.rollback()
                    finally:
                        release_connection(conn)   # ← SỬA Ở ĐÂY

                self.ocr_queue.task_done()

            except queue.Empty:
                if self.stop_event:
                    break
            except Exception as e:
                print(f"OCR Worker Error: {e}")

    def request_manual_ocr(self, track_id):
        if track_id in self.current_objects:
            obj = self.current_objects[track_id]
            print(f">> Clicked ID {track_id}. Requesting manual OCR...")
            self.ocr_queue.put((track_id, obj["crop"].copy(), True))

    def log_new_ship(self, track_id, class_name, crop_img=None):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM shiplog 
                WHERE track_id = %s AND session_id = %s
            """, (int(track_id), self.session_id))
            if cursor.fetchone()[0] > 0:
                return

            img_path = None
            if crop_img is not None and crop_img.size > 0:
                img_dir = os.path.join(self.output_folder, "ship_images")
                os.makedirs(img_dir, exist_ok=True)
                img_filename = f"ship_{track_id}_{int(time.time())}.jpg"
                img_path = os.path.join(img_dir, img_filename)
                cv2.imwrite(img_path, crop_img)

            video_name = os.path.basename(self.input_source) if isinstance(self.input_source, str) else "live"
            cursor.execute("""
                INSERT INTO shiplog 
                (ship_id, track_id, session_id, class_name, gio_phat_hien, hinh_anh_path, video_source, confidence)
                VALUES (NULL, %s, %s, %s, NOW(), %s, %s, NULL)
            """, (int(track_id), self.session_id, class_name, img_path, video_name))
            conn.commit()
        except Exception as e:
            print(f"DB Insert Error: {e}")
        finally:
            release_connection(conn)   # ← SỬA Ở ĐÂY

    def run(self, update_gui_callback):
        cap = cv2.VideoCapture(self.input_source)
        if not cap.isOpened():
            print(">> Không mở được video / camera!")
            return

        w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_vid = cap.get(cv2.CAP_PROP_FPS) or 30.0

        self.speed_estimator = SpeedEstimator(
            fps=fps_vid,
            pixel_to_meter=0.05,
            history_length=12,
            smoothing_window=5
        )

        save_path = os.path.join(self.output_folder, f"result_{os.path.basename(self.input_source)}")
        out = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps_vid, (w_vid, h_vid))

        frame_count = 0
        data_report = []

        print(">> Video processing started...")
        while cap.isOpened() and not self.stop_event:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % self.stride != 0:
                continue

            start_t = time.time()
            results = self.model.track(
                frame,
                conf=self.conf,
                imgsz=self.imgsz,
                persist=True,
                verbose=False,
                tracker="bytetrack.yaml"
            )
            res = results[0]
            annotated_frame = res.plot(labels=False)

            new_current_objects = {}
            current_ids_in_frame = set()

            if res.boxes.conf is not None:
                self.all_confs.extend(res.boxes.conf.cpu().numpy().tolist())

            if res.boxes.id is not None:
                boxes = res.boxes.xyxy.cpu().numpy().astype(int)
                ids = res.boxes.id.cpu().numpy().astype(int)
                cls_indices = res.boxes.cls.cpu().numpy().astype(int)
                names = self.model.names

                for i, (box, track_id, cls_idx) in enumerate(zip(boxes, ids, cls_indices)):
                    x1, y1, x2, y2 = box
                    current_ids_in_frame.add(track_id)
                    class_name = names[cls_idx]

                    crop_to_use = None
                    if track_id not in self.current_objects:
                        h, w, _ = frame.shape
                        cy1, cy2 = max(0, y1), min(h, y2)
                        cx1, cx2 = max(0, x1), min(w, x2)
                        crop_to_use = frame[cy1:cy2, cx1:cx2].copy()
                        self.log_new_ship(track_id, class_name, crop_to_use)
                    else:
                        crop_to_use = self.current_objects[track_id]["crop"]

                    _, speed_kmh = self.speed_estimator.update(track_id, box)

                    text_display = self.ocr_cache.get(track_id, {}).get("final", "...")

                    new_current_objects[track_id] = {
                        "bbox": (x1, y1, x2, y2),
                        "ocr": text_display,
                        "crop": crop_to_use,
                        "speed_kmh": speed_kmh,
                    }

                    short_label = f"id:{track_id} {self.class_short.get(class_name.lower(), class_name[0].upper())} {res.boxes.conf[i]:.2f}"
                    cv2.putText(annotated_frame, short_label,
                                (x1 + 5, y1 - 35 if text_display != "..." else y1 - 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    if text_display != "...":
                        cv2.putText(annotated_frame, text_display, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 255, 255), 2)

                    if speed_kmh > 0.5:
                        text_speed = f"{speed_kmh:.1f} km/h"
                        y_text = y1 - 55 if text_display != "..." else y1 - 45
                        cv2.putText(annotated_frame, text_speed, (x1, y_text),
                                    cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 255), 3)

            # ==================== UPDATE TỐC ĐỘ KHI MẤT TÀU ====================
            lost_ids = set(self.current_objects.keys()) - current_ids_in_frame
            conn = get_db_connection()
            if conn and lost_ids:
                try:
                    cursor = conn.cursor()
                    for tid in lost_ids:
                        avg_speed = self.speed_estimator.get_average_kmh(tid)
                        if avg_speed > 0:
                            cursor.execute(
                                "UPDATE shiplog SET toc_do_tb = %s WHERE track_id = %s AND session_id = %s",
                                (avg_speed, int(tid), self.session_id)
                            )
                    conn.commit()
                except Exception as e:
                    print(f"DB Update Speed Error: {e}")
                finally:
                    release_connection(conn)   # ← SỬA Ở ĐÂY

            self.current_objects = new_current_objects
            self.speed_estimator.cleanup(current_ids_in_frame)

            out.write(annotated_frame)
            process_ms = (time.time() - start_t) * 1000
            fps = 1000.0 / process_ms if process_ms > 0 else 0
            update_gui_callback(annotated_frame, fps)

            data_report.append({
                "Frame": frame_count,
                "FPS": fps,
                "Objects": len(current_ids_in_frame),
                "Time_ms": process_ms
            })

        print(">> Processing finished.")
        cap.release()
        out.release()

        # ==================== FINAL UPDATE ====================
        conn = get_db_connection()
        if conn and self.current_objects:
            try:
                cursor = conn.cursor()
                for tid in self.current_objects:
                    avg_speed = self.speed_estimator.get_average_kmh(tid)
                    if avg_speed > 0:
                        cursor.execute(
                            "UPDATE shiplog SET toc_do_tb = %s WHERE track_id = %s AND session_id = %s",
                            (avg_speed, int(tid), self.session_id)
                        )
                conn.commit()
            except Exception as e:
                print(f"Final DB Update Error: {e}")
            finally:
                release_connection(conn)   # ← SỬA Ở ĐÂY

        if data_report:
            processed_count = len(data_report)
            total_frames = frame_count
            ocr_data = {}
            for tid, info in self.ocr_cache.items():
                final_text = info.get("final")
                if final_text and final_text != "...":
                    ocr_data[tid] = final_text

            video_name = os.path.basename(self.input_source)
            model_name = os.path.basename(self.model_path)

            save_test_report(
                data=data_report,
                all_confs=self.all_confs,
                output_folder=self.output_folder,
                video_name=video_name,
                processed_count=processed_count,
                total_frames=total_frames,
                model_name=model_name,
                imgsz=self.imgsz,
                stride=self.stride,
                conf_thresh=self.conf,
                tag="AUTO_TEST",
                ocr_data=ocr_data
            )
            print(">> Báo cáo đã được tạo và lưu vào thư mục output.")

    def stop(self):
        self.stop_event = True