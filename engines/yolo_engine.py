import cv2
import time
import os
import threading
import queue
import pyodbc  
from ultralytics import YOLO
from engines.ocr_engine import ShipOCR
from utils.report_utils import save_test_report

class YoloTester:
    def __init__(self, model_path, input_source, output_folder,
                 conf, imgsz, stride, use_ocr=False):

        self.model_path = model_path
        self.input_source = input_source
        self.output_folder = output_folder
        self.conf = conf
        self.imgsz = imgsz
        self.stride = stride
        self.use_ocr = use_ocr
        self.stop_event = False

        # --- CẤU HÌNH DATABASE ---
        self.server = '.\\SQLEXPRESS'
        self.database = 'shipdb'
        self.db_conn = self.connect_db()

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
        self.current_objects = {}           # Lưu trữ đối tượng đang hiện hữu trong frame
        self.all_confs = []                 # Thu thập confidence cho báo cáo

    def connect_db(self):
        try:
            conn_str = (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                'Trusted_Connection=yes;'
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f">> Lỗi kết nối Database: {e}")
            return None

    def ocr_worker(self):
        """Worker xử lý ảnh từ hàng đợi và cập nhật Database"""
        print(">> OCR Worker started...")
        while True:
            try:
                item = self.ocr_queue.get(timeout=0.5)
                track_id, crop_img, is_priority = item
                
                results = self.ocr_engine.ocr_image(crop_img)
                
                if results:
                    text = results[0]["text"]
                    score = results[0]["score"]
                    print(f">> OCR Result [ID {track_id}]: {text} ({int(score*100)}%)")

                    if track_id not in self.ocr_cache:
                        self.ocr_cache[track_id] = {"texts": [], "final": None}
                    self.ocr_cache[track_id]["final"] = text

                    # Cập nhật số hiệu vào Database
                    if self.db_conn:
                        try:
                            cursor = self.db_conn.cursor()
                            query = "UPDATE shiplog SET so_hieu = ? WHERE track_id = ?"
                            cursor.execute(query, (text, int(track_id)))
                            self.db_conn.commit()
                        except Exception as db_e:
                            print(f"DB Update Error: {db_e}")
                
                self.ocr_queue.task_done()
            except queue.Empty:
                if self.stop_event: break
            except Exception as e:
                print(f"OCR Worker Error: {e}")

    def request_manual_ocr(self, track_id):
        if track_id in self.current_objects:
            obj = self.current_objects[track_id]
            print(f">> Clicked ID {track_id}. Requesting OCR...")
            self.ocr_queue.put((track_id, obj["crop"].copy(), True))

    def log_new_ship(self, track_id, class_name, crop_img=None):
        """Kiểm tra và ghi log tàu mới vào DB, lưu ảnh crop"""
        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM shiplog WHERE track_id = ?", (int(track_id),))
                if cursor.fetchone()[0] == 0:
                    img_path = None
                    if crop_img is not None and crop_img.size > 0:
                        img_dir = os.path.join(self.output_folder, "ship_images")
                        os.makedirs(img_dir, exist_ok=True)
                        img_filename = f"ship_{track_id}_{int(time.time())}.jpg"
                        img_path = os.path.join(img_dir, img_filename)
                        cv2.imwrite(img_path, crop_img)
                        print(f">> Saved crop image: {img_path}")

                    query = """
                        INSERT INTO shiplog 
                        (track_id, class_name, gio_phat_hien, hinh_anh_path) 
                        VALUES (?, ?, GETDATE(), ?)
                    """
                    cursor.execute(query, (int(track_id), class_name, img_path))
                    self.db_conn.commit()
                    print(f">> DB: Logged New Ship ID {track_id}")
            except Exception as e:
                print(f"DB Insert Error: {e}")

    def run(self, update_gui_callback):
        cap = cv2.VideoCapture(self.input_source)
        if not cap.isOpened():
            print(">> Không mở được video / camera!")
            return

        w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_vid = cap.get(cv2.CAP_PROP_FPS) or 30.0

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
            results = self.model.track(frame, conf=self.conf, imgsz=self.imgsz, persist=True, verbose=False)
            res = results[0]
            annotated_frame = res.plot()

            new_current_objects = {}
            current_ids_in_frame = []

            # Thu thập confidence
            if res.boxes.conf is not None:
                confs = res.boxes.conf.cpu().numpy()
                self.all_confs.extend(confs.tolist())

            if res.boxes and res.boxes.id is not None:
                boxes = res.boxes.xyxy.cpu().numpy().astype(int)
                ids = res.boxes.id.cpu().numpy().astype(int)
                cls_indices = res.boxes.cls.cpu().numpy().astype(int)
                names = self.model.names

                for box, track_id, cls_idx in zip(boxes, ids, cls_indices):
                    x1, y1, x2, y2 = box
                    current_ids_in_frame.append(track_id)
                    class_name = names[cls_idx]

                    # Crop và log tàu mới (chỉ lần đầu)
                    crop_to_use = None
                    if track_id not in self.current_objects:
                        h, w, _ = frame.shape
                        cy1, cy2 = max(0, y1), min(h, y2)
                        cx1, cx2 = max(0, x1), min(w, x2)
                        crop_to_use = frame[cy1:cy2, cx1:cx2].copy()
                        self.log_new_ship(track_id, class_name, crop_to_use)
                    else:
                        # Giữ crop lần đầu (để OCR ổn định)
                        crop_to_use = self.current_objects[track_id]["crop"]

                    text_display = self.ocr_cache.get(track_id, {}).get("final", "...")

                    new_current_objects[track_id] = {
                        "bbox": (x1, y1, x2, y2),
                        "ocr": text_display,
                        "crop": crop_to_use  # dùng crop lần đầu, không cập nhật mỗi frame
                    }

                    if text_display != "...":
                        cv2.putText(annotated_frame, text_display, (x1, y1-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            self.current_objects = new_current_objects

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
        if self.db_conn:
            self.db_conn.close()

        # Tạo báo cáo
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