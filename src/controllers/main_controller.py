# src/controllers/main_controller.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src.views.main_view import MainView
from src.controllers.log_controller import LogController
import threading
import os
import cv2
from src.engines.yolo_engine import YoloTester

CLASS_OPTIONS = ["speed boat", "passenger ship", "fishing boat"]

class MainController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Ship Detection System")
        self.engine = None
        self.thread = None
        self.selected_track_id = None

        self.callbacks = {
            "choose_model": self.choose_model,
            "choose_video": self.choose_video,
            "choose_output_folder": self.choose_output_folder,
            "start_process": self.start_process,
            "stop_process": self.stop_process,
            "refresh_current_page": self.refresh_current_page,
            "refresh_database": None,  # Sẽ được set sau khi khởi tạo log_controller
            "on_canvas_click": self.on_canvas_click,
            "on_tree_select": None,  # Từ log_controller
            "manual_ocr": None,  # Từ log_controller
            "on_closing": self.on_closing
        }
        
        self.view = MainView(self.root, self.callbacks)
        
        # Khởi tạo sub-controllers
        self.log_controller = LogController(self.root, self.view)
        
        # Cập nhật callbacks cho log_controller
        self.callbacks["refresh_database"] = self.log_controller.refresh_database
        self.callbacks["on_tree_select"] = self.log_controller.on_tree_select
        self.callbacks["manual_ocr"] = self.log_controller.manual_ocr
        
        # Reconnect callbacks vào view
        self.view.log_view.tree.bind("<<TreeviewSelect>>", self.callbacks["on_tree_select"])
        self.view.log_view.refresh_button.config(command=self.callbacks["refresh_database"])
        self.view.log_view.manual_ocr_btn.config(command=self.callbacks["manual_ocr"])
        
        # F5 binding để làm mới dữ liệu nhật ký
        def refresh_all(event=None):
            self.callbacks["refresh_database"]()
        self.root.bind("<F5>", refresh_all)
    # ==================== CÁC HÀM GIAO DIỆN ====================
    def choose_model(self):
        p = filedialog.askopenfilename(filetypes=[("Model", "*.pt *.engine")])
        if p: self.view.model_path.set(p)

    def choose_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi")])
        if p: self.view.video_path.set(p)

    def choose_output_folder(self):
        p = filedialog.askdirectory()
        if p: self.view.output_dir.set(p)

    def start_process(self):
        if not all([self.view.model_path.get(), self.view.video_path.get(), self.view.output_dir.get()]):
            self.view.show_warning("Thiếu thông tin", "Vui lòng chọn đầy đủ Model, Video và Output!")
            return
        
        # Kiểm tra text_model_path nếu use_ocr=True
        if self.view.use_ocr_var.get():
            if not self.view.ocr_model_path.get():
                self.view.show_warning("Thiếu thông tin", "Bạn phải chọn Model Text (OCR) nếu bật chế độ OCR!")
                return
        
        try:
            img_sz = int(self.view.img_size_entry.get())
            skp = int(self.view.skip_frame_entry.get())
        except ValueError:
            self.view.show_error("Lỗi", "Image Size và Skip Frame phải là số nguyên!")
            return
        
        self.selected_track_id = None
        os.makedirs(self.view.output_dir.get(), exist_ok=True)

        self.engine = YoloTester(
            model_path=self.view.model_path.get(),
            input_source=self.view.video_path.get(),
            output_folder=self.view.output_dir.get(),
            conf=self.view.conf_val.get(),
            imgsz=img_sz,
            stride=skp,
            use_ocr=self.view.use_ocr_var.get(),
            text_model_path=self.view.ocr_model_path.get() if self.view.use_ocr_var.get() else None,
            tracker=self.view.tracker_path.get()  # Truyền tracker path được chọn
        )
        
        # Store engine in view để LogController có thể truy cập
        self.view.engine = self.engine
        
        # Update output folder cho log_controller
        self.log_controller.set_output_folder(self.view.output_dir.get())
        
        self.thread = threading.Thread(target=self.engine.run, args=(self.view.update_frame,))
        self.thread.daemon = True
        self.thread.start()

    def stop_process(self):
        if self.engine: self.engine.stop()

    def refresh_current_page(self):
        for name, frame in self.view.frames.items():
            if frame.winfo_ismapped():
                if name == "database": self.callbacks["refresh_database"]()
                break

    def on_canvas_click(self, event):
        if not self.engine or not hasattr(self.view, 'last_scale'): 
            return
        x_click = (event.x - self.view.last_offset[0]) / self.view.last_scale
        y_click = (event.y - self.view.last_offset[1]) / self.view.last_scale
        found = False
        for tid, obj in getattr(self.engine, 'current_objects', {}).items():
            x1, y1, x2, y2 = obj["bbox"]
            if x1 <= x_click <= x2 and y1 <= y_click <= y2:
                self.selected_track_id = tid
                self.view.show_crop(obj.get("crop"))
                speed = obj.get("speed_kmh", 0.0)
                detail = f"🆔 ID Tracking: {tid}\n"
                if obj.get("ocr") != "...": 
                    detail += f"🔢 Số hiệu: {obj['ocr']}\n"
                detail += f"⚡ Tốc độ hiện tại: {speed:.1f} km/h\nĐang phân tích..."
                self.view.show_detail_text(detail)
                found = True
                break
        if not found:
            self.view.show_detail_text("Không tìm thấy tàu tại vị trí click.\nClick vào bounding box để xem chi tiết.")

    def on_auto_ocr_complete(self, track_id, so_hieu, confidence=1.0, 
                             class_name="Unknown", crop_path=""):
        """Callback OCR - delegate to log_controller"""
        self.log_controller.on_auto_ocr_complete(track_id, so_hieu, confidence, class_name, crop_path)

    def on_ship_action_click(self, event):
        """Xử lý click trên cột thao tác (Sửa/Xóa)"""
        # Not used anymore since ship_view is removed
        pass

    def on_closing(self):
        self.stop_process()
        self.root.destroy()

    def run(self):
        self.root.mainloop()