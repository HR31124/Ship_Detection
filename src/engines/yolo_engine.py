import cv2
import time
import os
import threading
import queue
from ultralytics import YOLO
from src.engines.ocr_engine import ShipOCR
from src.utils.report_utils import save_test_report
from src.utils.csv_logger import get_csv_logger
from src.engines.speed_estimator import SpeedEstimator

class YoloTester:
    def __init__(self, model_path, input_source, output_folder,
                 conf=0.5, imgsz=640, stride=1, use_ocr=False, text_model_path=None, tracker="bytetrack.yaml"):

        self.model_path = model_path
        self.input_source = input_source
        self.output_folder = output_folder
        self.conf = conf
        self.imgsz = imgsz
        self.stride = stride
        self.use_ocr = use_ocr
        self.tracker = tracker  # Lưu tracker path
        self.stop_event = False
        
        # Tạo thư mục ship_images nếu chưa tồn tại
        self.ship_images_dir = os.path.join(self.output_folder, "ship_images")
        os.makedirs(self.ship_images_dir, exist_ok=True)

        video_name = os.path.basename(input_source) if isinstance(input_source, str) else "live_camera"
        self.session_id = f"{video_name}_{int(time.time())}"
        print(f">> Session ID: {self.session_id}")

        print(f">> Loading YOLO: {model_path}")
        self.model = YOLO(model_path)

        self.ocr_queue = queue.Queue()
        self.ocr_engine = None
        self.text_model = None

        if use_ocr:
            # text_model_path là bắt buộc khi use_ocr=True
            if text_model_path is None:
                raise ValueError("❌ text_model_path là bắt buộc khi use_ocr=True")
            
            if not os.path.exists(text_model_path):
                raise FileNotFoundError(f"❌ Không tìm thấy text model: {text_model_path}")

            try:
                print(f">> Loading Text Detector: {text_model_path}")
                self.text_model = YOLO(text_model_path)
                
                print(f">> Loading OCR Engine (PaddleOCR)")
                self.ocr_engine = ShipOCR()
                
                # Khởi động OCR worker thread
                threading.Thread(target=self.ocr_worker, daemon=True).start()
                print(">> OCR Worker thread started")
            except Exception as e:
                print(f"❌ Lỗi Init OCR: {e}")
                self.ocr_engine = None
                self.text_model = None

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

    # ==================== OCR WORKER - 2-STAGE ARCHITECTURE ====================
    def ocr_worker(self):
        """
        2-Stage OCR Architecture:
        Stage 1: Text Detection - Sử dụng YOLO text_model để detect vùng chứa chữ/số trên tàu
        Stage 2: Text Recognition - Sử dụng PaddleOCR để nhận dạng chữ từ vùng detected
        """
        print(">> OCR Worker started (2-Stage: Text Detection → OCR)...")
        while True:
            try:
                item = self.ocr_queue.get(timeout=0.5)
                track_id, crop_img, is_priority, class_name, img_path = item

                if crop_img is None or crop_img.size == 0:
                    print(f">> ⚠️ Skip track_id {track_id}: crop_img is empty")
                    self.ocr_queue.task_done()
                    continue

                # ==================== STAGE 1: TEXT DETECTION ====================
                text_crop = self._detect_text_region(crop_img, track_id)

                if text_crop is None:
                    print(f">> ⚠️ Stage 1 Failed [track_id {track_id}]: Không detect được vùng chữ")
                    self.ocr_queue.task_done()
                    continue

                # ==================== STAGE 2: TEXT RECOGNITION ====================
                ocr_results = self._recognize_text(text_crop, track_id)

                if not ocr_results:
                    print(f">> ⚠️ Stage 2 Failed [track_id {track_id}]: PaddleOCR không đọc được")
                    self.ocr_queue.task_done()
                    continue

                # Lấy kết quả tốt nhất (confidence cao nhất)
                best = max(ocr_results, key=lambda x: x.get("score", 0))
                text = best["text"].strip().upper()
                score = best["score"]

                if len(text) < 3:  # bỏ qua số hiệu rác
                    print(f">> ⚠️ Skip [track_id {track_id}]: Text quá ngắn ('{text}')")
                    self.ocr_queue.task_done()
                    continue

                print(f">> ✅ OCR Result [track_id {track_id}]: {text} ({score:.1%})")

                if track_id not in self.ocr_cache:
                    self.ocr_cache[track_id] = {"texts": [], "final": None}
                self.ocr_cache[track_id]["final"] = text

                # ==================== CSV OPERATION ====================
                self._update_csv_after_ocr(track_id, text, score, class_name, img_path)

                self.ocr_queue.task_done()

            except queue.Empty:
                if self.stop_event:
                    break
            except Exception as e:
                print(f"❌ OCR Worker Error: {e}")
                try:
                    self.ocr_queue.task_done()
                except:
                    pass

    # ==================== STAGE 1: TEXT DETECTION ====================
    def _detect_text_region(self, ship_crop, track_id):
        """
        Sử dụng YOLO text_model để phát hiện vùng chứa chữ/số trên ảnh tàu.
        
        Args:
            ship_crop: Ảnh tàu đã crop từ frame chính
            track_id: ID của track hiện tại
            
        Returns:
            text_crop: Vùng chứa chữ đã crop, hoặc None nếu không tìm thấy
        """
        try:
            if self.text_model is None:
                return None

            # Run text detection
            text_results = self.text_model(ship_crop, conf=0.5, verbose=False)

            text_crop = None

            for result in text_results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                # Lấy bounding box có confidence cao nhất
                boxes = result.boxes
                conf_scores = boxes.conf.cpu().numpy()
                best_idx = conf_scores.argmax()

                box = boxes.xyxy[best_idx].cpu().numpy().astype(int)
                x1, y1, x2, y2 = box

                # Thêm padding để đảm bảo không bị cắt mất chữ
                pad = 5
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(ship_crop.shape[1], x2 + pad)
                y2 = min(ship_crop.shape[0], y2 + pad)

                # Check kích thước vùng cắt hợp lệ
                if x2 - x1 < 10 or y2 - y1 < 10:
                    print(f">> ⚠️ Text region quá nhỏ: {x2-x1}x{y2-y1}")
                    continue

                text_crop = ship_crop[y1:y2, x1:x2].copy()
                print(f">> 🔍 Stage 1 OK [track_id {track_id}]: Detected text region {x2-x1}x{y2-y1}")
                break

            return text_crop

        except Exception as e:
            print(f"❌ Text Detection Error [track_id {track_id}]: {e}")
            return None

    # ==================== STAGE 2: TEXT RECOGNITION ====================
    def _recognize_text(self, text_crop, track_id):
        """
        Sử dụng PaddleOCR để nhận dạng chữ từ vùng text_crop đã detect ở Stage 1.
        
        Args:
            text_crop: Vùng chứa chữ đã crop từ Stage 1
            track_id: ID của track hiện tại
            
        Returns:
            ocr_results: List các kết quả OCR [{text, score, box}, ...]
        """
        try:
            if self.ocr_engine is None:
                return None

            results = self.ocr_engine.ocr_image(text_crop)

            if not results:
                return None

            print(f">> 🔤 Stage 2 OK [track_id {track_id}]: PaddleOCR found {len(results)} texts")
            return results

        except Exception as e:
            print(f"❌ Text Recognition Error [track_id {track_id}]: {e}")
            return None

    # ==================== CSV UPDATE ====================
    def _update_csv_after_ocr(self, track_id, text, score, class_name, img_path):
        """
        Cập nhật thông tin OCR vào CSV file
        Sử dụng class_name từ YOLO detection và img_path để lưu thông tin tàu.
        """
        try:
            csv_logger = get_csv_logger(self.output_folder)
            
            # Cập nhật log với OCR result
            csv_logger.update_log(
                track_id=int(track_id),
                session_id=self.session_id,
                so_hieu_ocr=text,
                do_tin_cay_ocr=score,
                hinh_anh_path=img_path if img_path else ""
            )
            
            print(f">> ✅ Cập nhật CSV: so_hieu={text} | track_id={track_id} | confidence={score:.1%}")
            
        except Exception as e:
            print(f"❌ CSV Error (update after OCR): {e}")

    # ==================== REQUEST MANUAL OCR (khi user click) ====================
    def request_manual_ocr(self, track_id):
        """
        Khi user click vào object, đưa vào queue để OCR xử lý.
        Hỗ trợ 2-Stage OCR architecture.
        Lưu ý: Manual OCR có thể không có img_path mới (img_path=None).
        """
        if not self.use_ocr or self.ocr_engine is None:
            print(">> ⚠️ OCR is not enabled or not initialized")
            return

        if track_id not in self.current_objects:
            print(f">> ⚠️ Track ID {track_id} không tìm thấy")
            return

        obj = self.current_objects[track_id]
        crop_img = obj.get("crop")
        class_name = obj.get("class_name", "Unknown")

        if crop_img is None or crop_img.size == 0:
            print(f">> ⚠️ Ship crop is empty for track_id {track_id}")
            return

        print(f">> 📌 Requesting manual OCR for track_id {track_id}...")
        # img_path=None do manual OCR không lấy ảnh mới từ DB
        self.ocr_queue.put((track_id, crop_img.copy(), True, class_name, None))

    def log_new_ship(self, track_id, class_name, crop_img=None):
        """
        Ghi nhận detection mới vào CSV file
        Nếu use_ocr=True, tự động queue vào OCR worker.
        """
        try:
            csv_logger = get_csv_logger(self.output_folder)
            
            # Kiểm tra xem track_id đã được log chưa trong session này
            existing = csv_logger.get_log_by_track_id(int(track_id), self.session_id)
            if existing is not None:
                return  # Đã log rồi, không log lại
            
            img_path = ""
            if crop_img is not None and crop_img.size > 0:
                img_filename = f"ship_{self.session_id}_{track_id}_{int(time.time())}.jpg"
                img_full_path = os.path.join(self.ship_images_dir, img_filename)
                cv2.imwrite(img_full_path, crop_img)
                
                # Lưu đường dẫn relative từ output folder (output/ship_images/...)
                img_path = os.path.join("output", "ship_images", img_filename)

                # Tự động queue vào OCR nếu enabled
                if self.use_ocr and self.ocr_engine is not None:
                    self.ocr_queue.put((track_id, crop_img.copy(), False, class_name, img_path))
                    print(f">> 🔄 Auto-queued to OCR for track_id {track_id} ({class_name}) | Ảnh: {img_path}")

            video_name = os.path.basename(self.input_source) if isinstance(self.input_source, str) else "live"
            
            # Append vào CSV
            csv_logger.append_log(
                track_id=int(track_id),
                session_id=self.session_id,
                class_name=class_name,
                video_source=video_name,
                so_hieu_ocr="N/A",
                do_tin_cay_ocr=0.0,
                toc_do_tb=0.0,
                hinh_anh_path=img_path
            )
            print(f">> CSV: Logged New Detection track_id={track_id}")
        except Exception as e:
            print(f">> CSV Insert Error: {e}")

    def run(self, update_gui_callback):
        # (giữ nguyên nguyên bản phần run của bạn, không thay đổi gì)
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
                tracker=self.tracker  # Sử dụng tracker từ constructor
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

                    class_short_map = {
                        "fishing_boat": "F",
                        "speed_boat": "S",
                        "passenger": "P",
                        "passenger_ship": "P",
                    }
                    short_class = class_short_map.get(class_name.lower(), class_name[0].upper())

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
                        "class_name": class_name,  # Lưu class_name để dùng cho manual OCR
                    }

                    short_label = f"id:{track_id} {short_class} {res.boxes.conf[i]:.2f}"
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

            lost_ids = set(self.current_objects.keys()) - current_ids_in_frame
            csv_logger = get_csv_logger(self.output_folder)
            if lost_ids:
                try:
                    for tid in lost_ids:
                        avg_speed = self.speed_estimator.get_average_kmh(tid)
                        if avg_speed > 0:
                            csv_logger.update_log(
                                track_id=int(tid),
                                session_id=self.session_id,
                                toc_do_tb=avg_speed
                            )
                except Exception as e:
                    print(f">> CSV Update Speed Error: {e}")

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

        csv_logger = get_csv_logger(self.output_folder)
        if self.current_objects:
            try:
                for tid in self.current_objects:
                    avg_speed = self.speed_estimator.get_average_kmh(tid)
                    if avg_speed > 0:
                        csv_logger.update_log(
                            track_id=int(tid),
                            session_id=self.session_id,
                            toc_do_tb=avg_speed
                        )
            except Exception as e:
                print(f">> Final CSV Update Error: {e}")

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
        else:
            print(">> Không có dữ liệu để tạo báo cáo.")

    def stop(self):
        self.stop_event = True