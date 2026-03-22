# src/controllers/main_controller.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src.views.main_view import MainView
from src.utils.connect import get_db_connection, close_db_connection, release_connection
import threading
import os
import cv2
from src.engines.yolo_engine import YoloTester

CLASS_OPTIONS = ["speed boat", "passenger ship", "fishing boat"]

class MainController:
    def __init__(self, user_info=None):
        self.root = tk.Tk()
        self.user_info = user_info
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
            "refresh_database": self.refresh_database,
            "refresh_ship_list": self.refresh_ship_list,
            "on_canvas_click": self.on_canvas_click,
            "on_tree_select": self.on_tree_select,
            "on_ship_select": self.on_ship_select,
            "manual_ocr_hand": self.manual_ocr_hand,
            "manual_ocr_auto": self.manual_ocr_auto,
            "add_ship_dialog": self.add_ship_dialog,
            "edit_ship_dialog": self.edit_ship_dialog,
            "delete_ship": self.delete_ship,
            "logout": self.logout,
            "on_closing": self.on_closing
        }
        self.view = MainView(self.root, self.callbacks)

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
            use_ocr=self.view.use_ocr_var.get()
        )
        self.thread = threading.Thread(target=self.engine.run, args=(self.view.update_frame,))
        self.thread.daemon = True
        self.thread.start()

    def stop_process(self):
        if self.engine: self.engine.stop()

    def refresh_current_page(self):
        for name, frame in self.view.frames.items():
            if frame.winfo_ismapped():
                if name == "database": self.refresh_database()
                elif name == "ship_management": self.refresh_ship_list()
                break

    def refresh_database(self):
        conn = get_db_connection()
        if not conn:
            self.view.show_error("Lỗi Database", "Không thể kết nối đến cơ sở dữ liệu!")
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT track_id, class_name, COALESCE(so_hieu_ocr, 'N/A'),
                       toc_do_tb, gio_phat_hien, COALESCE(hinh_anh_path, ''),
                       COALESCE(video_source, 'Unknown')
                FROM shiplog ORDER BY gio_phat_hien DESC
            """)
            rows = cursor.fetchall()
            self.view.refresh_database_ui(rows)
        except Exception as e:
            self.view.show_error("Lỗi Truy vấn", f"Không thể tải dữ liệu:\n{str(e)}")
        finally:
            if conn: release_connection(conn)
        self.view.refresh_status.config(text="✅ Đã làm mới!")
        self.root.after(2000, lambda: self.view.refresh_status.config(text=""))

    def refresh_ship_list(self):
        conn = get_db_connection()
        if not conn:
            self.view.show_error("Lỗi Database", "Không thể kết nối đến cơ sở dữ liệu!")
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ship_id, so_hieu, class_name, anh_dai_dien, ngay_tao
                FROM ship ORDER BY ngay_tao DESC
            """)
            rows = cursor.fetchall()
            self.view.refresh_ship_list_ui(rows)
        except Exception as e:
            self.view.show_error("Lỗi Truy vấn", f"Không thể tải danh sách tàu:\n{str(e)}")
        finally:
            if conn: release_connection(conn)
        self.view.ship_refresh_status.config(text="✅ Đã làm mới!")
        self.root.after(2000, lambda: self.view.ship_refresh_status.config(text=""))

    def on_canvas_click(self, event):
        if not self.engine or not hasattr(self.view, 'last_scale'): return
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
                if obj.get("ocr") != "...": detail += f"🔢 Số hiệu: {obj['ocr']}\n"
                detail += f"⚡ Tốc độ hiện tại: {speed:.1f} km/h\nĐang phân tích..."
                self.view.show_detail_text(detail)
                found = True
                break
        if not found:
            self.view.show_detail_text("Không tìm thấy tàu tại vị trí click.\nClick vào bounding box để xem chi tiết.")

    def on_tree_select(self, event):
        selected = self.view.tree.selection()
        if not selected: return
        item_id = selected[0]
        values = self.view.tree.item(item_id, "values")
        img_path = self.view.tree_img_paths.get(item_id, "")
        info = (f"🆔 ID Tracking : {values[0]}\n"
                f"🚢 Loại tàu      : {values[1]}\n"
                f"🔢 Số hiệu (OCR) : {values[2]}\n"
                f"⚡ Tốc độ TB      : {values[3]} km/h\n"
                f"🕐 Giờ phát hiện : {values[4]}\n"
                f"📹 Nguồn video   : {values[5]}")
        self.view.show_db_info(info, img_path)

    def on_ship_select(self, event):
        selected = self.view.ship_tree.selection()
        if not selected: return
        item_id = selected[0]
        values = self.view.ship_tree.item(item_id, "values")
        img_path = self.view.ship_img_paths.get(item_id, "")
        info = (f"🔢 Số hiệu   : {values[0]}\n"
                f"🚢 Loại tàu  : {values[1]}\n"
                f"📅 Ngày tạo  : {values[2]}")
        self.view.show_ship_info(info, img_path)
        so_hieu = values[0]
        self.load_ship_history(so_hieu)

    def load_ship_history(self, so_hieu):
        for i in self.view.ship_history_tree.get_children():
            self.view.ship_history_tree.delete(i)
        conn = get_db_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gio_phat_hien, toc_do_tb, so_hieu_ocr, video_source
                FROM shiplog 
                WHERE so_hieu_ocr = %s 
                ORDER BY gio_phat_hien DESC
            """, (so_hieu,))
            rows = cursor.fetchall()
            for row in rows:
                toc_do = f"{row[1]:.1f}" if row[1] is not None else "N/A"
                self.view.ship_history_tree.insert("", tk.END, values=(
                    row[0], toc_do, row[2] or "N/A", row[3] or "Unknown"
                ))
        except Exception as e:
            print("Lỗi load lịch sử tàu:", e)
        finally:
            if conn: release_connection(conn)

    # ==================== 2 NÚT OCR ====================
    def manual_ocr_hand(self):
        selected = self.view.tree.selection()
        if not selected:
            self.view.show_warning("Chưa chọn", "Vui lòng chọn một tàu trong bảng trước!")
            return
        track_id = int(self.view.tree.item(selected[0], "values")[0])

        default_class = "Unknown"
        default_img = ""
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT class_name, hinh_anh_path 
                    FROM shiplog 
                    WHERE track_id = %s 
                    ORDER BY log_id DESC 
                    LIMIT 1
                """, (track_id,))
                row = cursor.fetchone()
                if row:
                    default_class = row[0] or "Unknown"
                    default_img = row[1] or ""
        except Exception as e:
            print(f"Lỗi lấy dữ liệu pre-fill: {e}")
        finally:
            if 'conn' in locals() and conn is not None:
                release_connection(conn)

        dialog = tk.Toplevel(self.root)
        dialog.title("OCR Thủ công - Nhập đầy đủ")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.grab_set()

        temp_image_path = tk.StringVar(value=default_img)

        tk.Label(dialog, text="Số hiệu tàu (*)", font=("Arial", 10)).pack(anchor="w", padx=25, pady=(20,5))
        e_sohieu = tk.Entry(dialog, font=("Arial", 11), width=42)
        e_sohieu.insert(0, self.view.tree.item(selected[0], "values")[2] if self.view.tree.item(selected[0], "values")[2] != "N/A" else "")
        e_sohieu.pack(padx=25, pady=3)

        tk.Label(dialog, text="Loại tàu", font=("Arial", 10)).pack(anchor="w", padx=25, pady=(10,5))
        e_class = ttk.Combobox(dialog, font=("Arial", 11), width=40, values=CLASS_OPTIONS, state="readonly")
        e_class.set(default_class)
        e_class.pack(padx=25, pady=3)

        tk.Label(dialog, text="Mô tả tàu", font=("Arial", 10)).pack(anchor="w", padx=25, pady=(10,5))
        e_mota = tk.Text(dialog, font=("Arial", 10), height=4, width=45)
        e_mota.pack(padx=25, pady=3)

        tk.Label(dialog, text="Ảnh đại diện", font=("Arial", 10)).pack(anchor="w", padx=25, pady=(10,5))
        frame_img = tk.Frame(dialog)
        frame_img.pack(fill=tk.X, padx=25)
        e_anh = tk.Entry(frame_img, textvariable=temp_image_path, state='readonly', width=35)
        e_anh.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        tk.Button(frame_img, text="📂 Chọn", command=lambda: temp_image_path.set(
            filedialog.askopenfilename(filetypes=[("Image", "*.jpg *.png *.jpeg")]))).pack(side=tk.LEFT)

        def save():
            sohieu = e_sohieu.get().strip()
            if not sohieu:
                self.view.show_warning("Thiếu dữ liệu", "Số hiệu không được để trống!")
                return

            conn = None
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT ship_id FROM ship WHERE so_hieu = %s", (sohieu,))
                    existing = cursor.fetchone()

                    if existing:
                        cursor.execute("""
                            UPDATE ship 
                            SET class_name = %s, mo_ta = %s, anh_dai_dien = %s, ngay_cap_nhat = NOW()
                            WHERE ship_id = %s
                        """, (e_class.get(), e_mota.get("1.0", tk.END).strip(), temp_image_path.get(), existing[0]))
                    else:
                        cursor.execute("""
                            INSERT INTO ship (so_hieu, class_name, mo_ta, anh_dai_dien, ngay_tao)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (sohieu, e_class.get(), e_mota.get("1.0", tk.END).strip(), temp_image_path.get()))

                    cursor.execute("""
                        UPDATE shiplog 
                        SET so_hieu_ocr = %s, do_tin_cay_ocr = 1.0 
                        WHERE track_id = %s 
                        AND log_id = (SELECT MAX(log_id) FROM shiplog WHERE track_id = %s)
                    """, (sohieu, track_id, track_id))

                    conn.commit()
                    self.view.show_info("Thành công", f"Đã cập nhật OCR: {sohieu}")
                    dialog.destroy()
                    self.refresh_database()
                    self.refresh_ship_list()
            except Exception as ex:
                self.view.show_error("Lỗi Database", str(ex))
            finally:
                if conn:
                    release_connection(conn)

        tk.Button(dialog, text="💾 LƯU & CẬP NHẬT OCR", bg="#28a745", fg="white", 
                  font=("Arial", 12, "bold"), height=2, command=save).pack(pady=20)

    def manual_ocr_auto(self):
        selected = self.view.tree.selection()
        if not selected:
            self.view.show_warning("Chưa chọn", "Vui lòng chọn một tàu trong bảng trước!")
            return
        track_id = int(self.view.tree.item(selected[0], "values")[0])

        if self.engine and track_id in getattr(self.engine, 'current_objects', {}):
            self.engine.request_manual_ocr(track_id)
            self.view.show_info("Đã gửi", f"Đã yêu cầu OCR tự động cho ID {track_id}")
        else:
            self.view.show_warning("Cảnh báo", "Hệ thống giám sát chưa chạy.\nKhông thể thực hiện OCR tự động lúc này.")

    # ==================== CRUD TÀU ====================
    def add_ship_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Thêm tàu mới")
        dialog.geometry("450x380")
        dialog.resizable(False, False)
        dialog.grab_set()
        temp_image_path = tk.StringVar()
        tk.Label(dialog, text="Số hiệu tàu (*)", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_sohieu = tk.Entry(dialog, font=("Arial", 11), width=40)
        e_sohieu.pack(padx=20, pady=2)
        tk.Label(dialog, text="Loại tàu", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_class = ttk.Combobox(dialog, font=("Arial", 11), width=38, values=CLASS_OPTIONS, state="readonly")
        e_class.set(CLASS_OPTIONS[0])
        e_class.pack(padx=20, pady=2)
        tk.Label(dialog, text="Ảnh đại diện", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        frame_path = tk.Frame(dialog)
        frame_path.pack(fill=tk.X, padx=20)
        e_anh = tk.Entry(frame_path, font=("Arial", 10), textvariable=temp_image_path, width=30, state='readonly')
        e_anh.pack(side=tk.LEFT, padx=(0, 5))
        def browse_image():
            p = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
            if p: temp_image_path.set(p)
        tk.Button(frame_path, text="Chọn file...", command=browse_image).pack(side=tk.LEFT)
        def save():
            so_hieu = e_sohieu.get().strip()
            if not so_hieu:
                self.view.show_warning("Thiếu dữ liệu", "Số hiệu tàu không được để trống!")
                return
            conn = None
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO ship (so_hieu, class_name, anh_dai_dien, ngay_tao) VALUES (%s, %s, %s, NOW())",
                                   (so_hieu, e_class.get(), temp_image_path.get()))
                    conn.commit()
                    self.view.show_info("Thành công", f"Đã thêm tàu {so_hieu}!")
                    dialog.destroy()
                    self.refresh_ship_list()
            except Exception as ex:
                self.view.show_error("Lỗi Database", str(ex))
            finally:
                if conn: release_connection(conn)
        tk.Button(dialog, text="LƯU TÀU", bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                  height=2, width=20, command=save).pack(pady=30)

    def edit_ship_dialog(self):
        selected = self.view.ship_tree.selection()
        if not selected:
            self.view.show_warning("Chưa chọn", "Vui lòng chọn một tàu để sửa!")
            return
        item = self.view.ship_tree.item(selected[0])
        sohieu = item['values'][0]
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT class_name, anh_dai_dien FROM ship WHERE so_hieu = %s", (sohieu,))
            row = cursor.fetchone()
            release_connection(conn)

        if not row: return
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Sửa tàu: {sohieu}")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()
        temp_image_path = tk.StringVar(value=row[1] or "")
        tk.Label(dialog, text="Loại tàu", font=("Arial", 10)).pack(anchor="w", padx=20, pady=(20, 5))
        e_class = ttk.Combobox(dialog, font=("Arial", 11), width=40, values=CLASS_OPTIONS, state="readonly")
        current_class = row[0] or ""
        e_class.set(current_class if current_class in CLASS_OPTIONS else CLASS_OPTIONS[0])
        e_class.pack(padx=20, pady=5)
        tk.Label(dialog, text="Ảnh đại diện", font=("Arial", 10)).pack(anchor="w", padx=20, pady=(10, 5))
        frame_path = tk.Frame(dialog)
        frame_path.pack(fill=tk.X, padx=20)
        e_anh = tk.Entry(frame_path, font=("Arial", 10), textvariable=temp_image_path, width=35, state='readonly')
        e_anh.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        def browse_image():
            p = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
            if p: temp_image_path.set(p)
        tk.Button(frame_path, text="📂 Chọn file...", command=browse_image, bg="#3498db", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        def save_edit():
            conn = None
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE ship SET class_name=%s, anh_dai_dien=%s, ngay_cap_nhat=NOW() WHERE so_hieu=%s",
                                   (e_class.get(), temp_image_path.get(), sohieu))
                    conn.commit()
                    self.view.show_info("Thành công", f"Đã cập nhật tàu {sohieu}!")
                    dialog.destroy()
                    self.refresh_ship_list()
            except Exception as ex:
                self.view.show_error("Lỗi", str(ex))
            finally:
                if conn: release_connection(conn)
        tk.Button(dialog, text="CẬP NHẬT", bg="#ffc107", fg="black", font=("Arial", 12, "bold"), height=2, width=20, command=save_edit).pack(pady=30)

    def delete_ship(self):
        selected = self.view.ship_tree.selection()
        if not selected:
            self.view.show_warning("Chưa chọn", "Vui lòng chọn tàu cần xóa!")
            return
        sohieu = self.view.ship_tree.item(selected[0])['values'][0]
        if not self.view.ask_yesno("Xác nhận", f"Bạn có chắc muốn xóa tàu\n{sohieu}?"): return
        conn = None
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ship WHERE so_hieu = %s", (sohieu,))
                conn.commit()
                self.view.show_info("Thành công", f"Đã xóa tàu {sohieu}")
                self.refresh_ship_list()
        except Exception as e:
            self.view.show_error("Lỗi", str(e))
        finally:
            if conn: release_connection(conn)

    def logout(self):
        if self.view.ask_yesno("Đăng xuất", "Bạn có chắc muốn đăng xuất?"):
            self.stop_process()
            self.root.destroy()
            import os
            os.system('python src/main.py')

    def on_closing(self):
        self.stop_process()
        close_db_connection()
        self.root.destroy()

    def run(self):
        self.root.mainloop()