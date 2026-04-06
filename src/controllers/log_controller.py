import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import os
from src.utils.csv_logger import get_csv_logger
from src.engines.ocr_engine import ShipOCR
from datetime import datetime
from pathlib import Path


class LogController:
    """Controller quản lý Nhật ký phát hiện tàu (CSV-based)"""
    
    def __init__(self, root, view):
        self.root = root
        self.view = view
        self.current_output_folder = "output"  # Mặc định
    
    def set_output_folder(self, folder):
        """Cập nhật thư mục output cho CSV logger"""
        self.current_output_folder = folder
    
    def refresh_database(self):
        """Làm mới dữ liệu nhật ký từ CSV"""
        try:
            csv_logger = get_csv_logger(self.current_output_folder)
            logs = csv_logger.get_all_logs()
            
            if not logs:
                self.view.refresh_database_ui([])
                self.view.log_view.refresh_status.config(text="✅ Không có dữ liệu")
                return
            
            # Chuyển định dạng logs thành tuples để tương thích với UI
            rows = []
            for log in logs:
                row = (
                    log.get('track_id', ''),
                    log.get('class_name', ''),
                    log.get('so_hieu_ocr', 'N/A'),
                    log.get('toc_do_tb', ''),
                    log.get('gio_phat_hien', ''),
                    log.get('hinh_anh_path', ''),
                    log.get('video_source', 'Unknown'),
                )
                rows.append(row)
            
            self.view.refresh_database_ui(rows)
            self.view.log_view.refresh_status.config(text="✅ Đã làm mới!")
            self.root.after(2000, lambda: self.view.log_view.refresh_status.config(text=""))
            
        except Exception as e:
            self.view.show_error("Lỗi" , f"Không thể tải dữ liệu:\n{str(e)}")

    def on_tree_select(self, event):
        """Xử lý khi người dùng chọn một dòng trong bảng nhật ký"""
        selected = self.view.log_view.tree.selection()
        if not selected: 
            return
        item_id = selected[0]
        values = self.view.log_view.tree.item(item_id, "values")
        img_path = self.view.log_view.tree_img_paths.get(item_id, "")
        
        toc_do_display = values[3] if len(values) > 3 else "N/A"
        try:
            toc_do_display = f"{float(toc_do_display):.1f}" if toc_do_display else "N/A"
        except:
            toc_do_display = "N/A"
        
        info = (f"🆔 ID Tracking : {values[0]}\n"
                f"🚢 Loại tàu      : {values[1]}\n"
                f"🔢 Số hiệu (OCR) : {values[2]}\n"
                f"⚡ Tốc độ TB      : {toc_do_display} km/h\n"
                f"🕐 Giờ phát hiện : {values[4]}\n"
                f"📹 Nguồn video   : {values[6] if len(values) > 6 else 'Unknown'}")
        self.view.show_db_info(info, img_path)

    def load_ship_history(self, so_hieu):
        """Load lịch sử phát hiện của một tàu"""
        self.view.log_view.ship_history_tree.delete(*self.view.log_view.ship_history_tree.get_children())
        
        try:
            csv_logger = get_csv_logger(self.current_output_folder)
            logs = csv_logger.get_logs_by_so_hieu(so_hieu)
            
            if not logs:
                return
            
            for log in logs:
                toc_do = f"{log.get('toc_do_tb', 0):.1f}" if log.get('toc_do_tb') else "N/A"
                self.view.log_view.ship_history_tree.insert("", tk.END, values=(
                    log.get('gio_phat_hien', ''),
                    toc_do,
                    log.get('so_hieu_ocr', 'N/A'),
                    log.get('video_source', 'Unknown')
                ))
        except Exception as e:
            print(f"Lỗi load lịch sử tàu: {e}")

    def manual_ocr(self):
        """OCR thủ công từ ảnh lưu trữ"""
        selected = self.view.log_view.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một tàu trong bảng trước!")
            return
        
        item_id = selected[0]
        values = self.view.log_view.tree.item(item_id, "values")
        track_id = int(values[0])
        img_rel_path = self.view.log_view.tree_img_paths.get(item_id, "")
        
        # Thử cách 1: Request từ engine nếu đang chạy (real-time)
        engine = getattr(self.view, 'engine', None)
        if engine and track_id in getattr(engine, 'current_objects', {}):
            if engine.use_ocr and engine.ocr_engine:
                engine.request_manual_ocr(track_id)
                messagebox.showinfo("Đã gửi", f"Đã yêu cầu OCR cho ID {track_id}")
                return
        
        # Cách 2: OCR từ ảnh lưu trữ (fallback)
        if img_rel_path:
            # Tạo full path từ relative path
            img_full_path = os.path.join(self.current_output_folder, img_rel_path)
            if os.path.exists(img_full_path):
                self.manual_ocr_from_file(track_id, img_full_path)
            else:
                messagebox.showwarning("Cảnh báo", f"Không tìm thấy ảnh:\n{img_full_path}")
        else:
            messagebox.showwarning("Cảnh báo", "Không có ảnh lưu trữ hoặc hệ thống giám sát chưa chạy.")

    def manual_ocr_from_file(self, track_id, img_path):
        """OCR từ file ảnh"""
        try:
            if not os.path.exists(img_path):
                messagebox.showerror("Lỗi", f"Không tìm thấy file ảnh:\n{img_path}")
                return
            
            # Load ảnh
            crop = cv2.imread(img_path)
            if crop is None:
                messagebox.showerror("Lỗi", "Không thể đọc file ảnh!")
                return
            
            messagebox.showinfo("Đang xử lý", "Đang OCR...")
            
            # Kiểm tra nếu engine có hỗ trợ 2-Stage OCR
            engine = getattr(self.view, 'engine', None)
            text, score = None, 0.0
            
            if engine and engine.use_ocr and engine.text_model and engine.ocr_engine:
                # ==================== 2-STAGE OCR ====================
                print(f">> Sử dụng 2-Stage OCR (Engine)")
                
                try:
                    # Stage 1: Text Detection
                    text_results = engine.text_model(crop, conf=0.5, verbose=False)
                    text_crop = None
                    
                    for result in text_results:
                        if result.boxes is None or len(result.boxes) == 0:
                            continue
                        boxes = result.boxes
                        conf_scores = boxes.conf.cpu().numpy()
                        best_idx = conf_scores.argmax()
                        box = boxes.xyxy[best_idx].cpu().numpy().astype(int)
                        x1, y1, x2, y2 = box
                        
                        pad = 5
                        x1 = max(0, x1 - pad)
                        y1 = max(0, y1 - pad)
                        x2 = min(crop.shape[1], x2 + pad)
                        y2 = min(crop.shape[0], y2 + pad)
                        
                        if x2 - x1 >= 10 and y2 - y1 >= 10:
                            text_crop = crop[y1:y2, x1:x2].copy()
                            break
                    
                    if text_crop is None:
                        raise Exception("Stage 1 Failed: Không detect được vùng chữ")
                    
                    # Stage 2: Text Recognition
                    results = engine.ocr_engine.ocr_image(text_crop)
                    if results:
                        best = max(results, key=lambda x: x.get("score", 0))
                        text = best["text"].strip().upper()
                        score = best["score"]
                    else:
                        raise Exception("Stage 2 Failed: PaddleOCR không đọc được")
                        
                except Exception as e:
                    print(f">> 2-Stage OCR Error: {e}. Fallback to PaddleOCR...")
                    text, score = None, 0.0
            
            # ==================== FALLBACK: PaddleOCR ONLY ====================
            if text is None:
                print(f">> Sử dụng PaddleOCR (Fallback)")
                ocr = ShipOCR()
                results = ocr.ocr_image(crop)
                
                if not results:
                    messagebox.showwarning("Kết quả", "OCR không đọc được ký tự nào.")
                    return
                
                best = max(results, key=lambda x: x.get("score", 0))
                text = best["text"].strip().upper()
                score = best["score"]
            
            print(f">> OCR Result [track_id {track_id}]: {text} ({score:.1%})")
            
            # Update CSV
            csv_logger = get_csv_logger(self.current_output_folder)
            csv_logger.update_log(
                track_id=track_id,
                session_id="",
                so_hieu_ocr=text,
                do_tin_cay_ocr=score
            )
            
            messagebox.showinfo("Thành công", f"OCR Result: {text}\nĐộ tin cây: {score:.1%}")
            self.refresh_database()
            
        except Exception as e:
            messagebox.showerror("Lỗi OCR", str(e))
