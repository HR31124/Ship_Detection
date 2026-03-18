import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import threading
import os
from utils.connect import get_db_connection, close_db_connection
from engines.yolo_engine import YoloTester

CLASS_OPTIONS = ["speed boat", "passenger ship", "fishing boat"]

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ thống Giám sát Tàu biển - YOLO & OCR")
        self.root.geometry("1400x900")

        self.output_dir = tk.StringVar()
        self.model_path = tk.StringVar()
        self.video_path = tk.StringVar()
        self.conf_val = tk.DoubleVar(value=0.5)
        self.use_ocr_var = tk.BooleanVar(value=True)
        self.selected_track_id = None
        self.tree_img_paths = {}
        self.ship_img_paths = {}

        self.setup_navbar()

        self.container = tk.Frame(self.root)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.frames = {}
        self.setup_monitoring_page()
        self.setup_database_page()
        self.setup_ship_management_page()

        self.show_frame("monitoring")

        self.root.bind("<F5>", lambda e: self.refresh_current_page())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_navbar(self):
        navbar = tk.Frame(self.root, bg="#2c3e50", height=50)
        navbar.pack(side=tk.TOP, fill=tk.X)

        nav_style = {
            "bg": "#2c3e50",
            "fg": "white",
            "font": ("Arial", 11, "bold"),
            "relief": "flat",
            "activebackground": "#34495e",
            "activeforeground": "white",
            "padx": 20
        }

        tk.Button(navbar, text="🏠 Hệ thống giám sát", **nav_style,
                  command=lambda: self.show_frame("monitoring")).pack(side=tk.LEFT)
        tk.Button(navbar, text="📊 Nhật ký phát hiện", **nav_style,
                  command=lambda: self.show_frame("database")).pack(side=tk.LEFT)
        tk.Button(navbar, text="🚢 Quản lý tàu", **nav_style,
                  command=lambda: self.show_frame("ship_management")).pack(side=tk.LEFT)
        tk.Button(navbar, text="🚪 Đăng xuất", **nav_style,
                  command=self.logout).pack(side=tk.RIGHT)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name in ["database", "ship_management"]:
            self.refresh_current_page()

    def refresh_current_page(self):
        for name, frame in self.frames.items():
            if frame.winfo_ismapped():
                if name == "database":
                    self.refresh_database()
                elif name == "ship_management":
                    self.refresh_ship_list()
                break

    def setup_monitoring_page(self):
        page = tk.Frame(self.container, bg="white")
        self.frames["monitoring"] = page
        page.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        control_frame = tk.Frame(page, bg="#f0f0f0", width=350)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        tk.Label(control_frame, text="BẢNG ĐIỀU KHIỂN", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

        tk.Button(control_frame, text="📁 Chọn Model", command=self.choose_model).pack(fill=tk.X, pady=5)
        tk.Label(control_frame, textvariable=self.model_path, fg="blue", font=("Arial", 9), wraplength=300, bg="#f0f0f0").pack()

        tk.Button(control_frame, text="🎬 Chọn Video", command=self.choose_video).pack(fill=tk.X, pady=5)
        tk.Label(control_frame, textvariable=self.video_path, fg="blue", font=("Arial", 9), wraplength=300, bg="#f0f0f0").pack()

        tk.Button(control_frame, text="📂 Chọn Output Folder", command=self.choose_output_folder).pack(fill=tk.X, pady=5)
        tk.Label(control_frame, textvariable=self.output_dir, fg="green", font=("Arial", 9), wraplength=300, bg="#f0f0f0").pack()

        config_group = tk.LabelFrame(control_frame, text="Cấu hình tham số", bg="#f0f0f0", padx=10, pady=10)
        config_group.pack(fill=tk.X, pady=15)

        row1 = tk.Frame(config_group, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)
        tk.Label(row1, text="Image Size:", bg="#f0f0f0", width=12, anchor="w").pack(side=tk.LEFT)
        self.img_size_entry = tk.Entry(row1, width=10)
        self.img_size_entry.insert(0, "640")
        self.img_size_entry.pack(side=tk.LEFT)

        row2 = tk.Frame(config_group, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=5)
        tk.Label(row2, text="Skip Frame:", bg="#f0f0f0", width=12, anchor="w").pack(side=tk.LEFT)
        self.skip_frame_entry = tk.Entry(row2, width=10)
        self.skip_frame_entry.insert(0, "3")
        self.skip_frame_entry.pack(side=tk.LEFT)

        tk.Label(config_group, text="Conf Thresh:", bg="#f0f0f0").pack(anchor="w", pady=(5, 0))
        tk.Scale(config_group, from_=0.0, to=1.0, resolution=0.01,
                 orient=tk.HORIZONTAL, variable=self.conf_val, bg="#f0f0f0").pack(fill=tk.X)

        tk.Checkbutton(control_frame, text="Kích hoạt nhận diện OCR", variable=self.use_ocr_var,
                       font=("Arial", 10, "italic"), bg="#f0f0f0").pack(pady=10)

        tk.Button(control_frame, text="▶ BẮT ĐẦU", bg="#27ae60", fg="white", font=("Arial", 12, "bold"),
                  height=2, command=self.start_process).pack(fill=tk.X, pady=5)
        tk.Button(control_frame, text="⏹ DỪNG", bg="#c0392b", fg="white", command=self.stop_process).pack(fill=tk.X)

        self.detail_frame = tk.Frame(page, width=300, bg="white")
        self.detail_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        tk.Label(self.detail_frame, text="CHI TIẾT TÀU", font=("Arial", 12, "bold"), bg="white").pack(pady=10)
        self.detail_canvas = tk.Canvas(self.detail_frame, width=280, height=200, bg="gray")
        self.detail_canvas.pack(pady=5)
        self.detail_text = tk.Label(self.detail_frame, text="Click vào tàu trên video để xem chi tiết...",
                                    font=("Arial", 11), wraplength=280, justify=tk.LEFT, bg="white")
        self.detail_text.pack()

        self.canvas_video = tk.Canvas(page, bg="black")
        self.canvas_video.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas_video.bind("<Button-1>", self.on_canvas_click)

    def setup_database_page(self):
        page = tk.Frame(self.container, bg="#ecf0f1")
        self.frames["database"] = page
        page.grid(row=0, column=0, sticky="nsew")

        header_frame = tk.Frame(page, bg="#ecf0f1")
        header_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(header_frame, text="NHẬT KÝ PHÁT HIỆN",
                 font=("Arial", 18, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)

        self.refresh_status = tk.Label(header_frame, text="", fg="#27ae60",
                                       bg="#ecf0f1", font=("Arial", 10, "italic"))
        self.refresh_status.pack(side=tk.RIGHT, padx=10)

        tk.Button(header_frame, text="🔄 Làm mới (F5)",
                  command=self.refresh_database,
                  bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
                  padx=15, pady=5, relief="flat", cursor="hand2").pack(side=tk.RIGHT)

        main_frame = tk.Frame(page, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        tree_frame = tk.Frame(main_frame, bg="#ecf0f1")
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Class", "SoHieuOCR", "TocDo", "Gio", "Video"), show='headings', height=20)
        self.tree.heading("ID", text="ID Tracking")
        self.tree.heading("Class", text="Loại tàu")
        self.tree.heading("SoHieuOCR", text="Số hiệu (OCR)")
        self.tree.heading("TocDo", text="Tốc độ TB (km/h)")
        self.tree.heading("Gio", text="Giờ phát hiện")
        self.tree.heading("Video", text="Nguồn video")

        self.tree.column("ID", anchor=tk.CENTER, width=100)
        self.tree.column("Class", anchor=tk.CENTER, width=140)
        self.tree.column("SoHieuOCR", anchor=tk.CENTER, width=130)
        self.tree.column("TocDo", anchor=tk.CENTER, width=120)
        self.tree.column("Gio", anchor=tk.CENTER, width=160)
        self.tree.column("Video", anchor=tk.CENTER, width=180)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        img_panel = tk.Frame(main_frame, bg="white", width=320, relief="ridge", bd=2)
        img_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        img_panel.pack_propagate(False)

        tk.Label(img_panel, text="🚢 ẢNH TÀU", font=("Arial", 13, "bold"), bg="white").pack(pady=12)

        self.db_img_canvas = tk.Canvas(img_panel, width=290, height=260, bg="#dddddd")
        self.db_img_canvas.pack(pady=5, padx=10)
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh",
                                       fill="gray", font=("Arial", 12))

        self.db_info_label = tk.Label(img_panel, text="", font=("Arial", 10),
                                      bg="white", wraplength=290, justify=tk.LEFT)
        self.db_info_label.pack(pady=8, padx=10)

        tk.Button(img_panel, text="🔍 OCR LẠI (Thử lại số hiệu)",
                  command=self.manual_ocr_selected_ship,
                  bg="#e67e22", fg="white", font=("Arial", 11, "bold"),
                  padx=10, pady=8).pack(pady=10)

    def setup_ship_management_page(self):
        page = tk.Frame(self.container, bg="#ecf0f1")
        self.frames["ship_management"] = page
        page.grid(row=0, column=0, sticky="nsew")

        header_frame = tk.Frame(page, bg="#ecf0f1")
        header_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(header_frame, text="🚢 QUẢN LÝ TÀU",
                 font=("Arial", 18, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)

        self.ship_refresh_status = tk.Label(header_frame, text="", fg="#27ae60",
                                            bg="#ecf0f1", font=("Arial", 10, "italic"))
        self.ship_refresh_status.pack(side=tk.RIGHT, padx=10)

        tk.Button(header_frame, text="🔄 Làm mới", command=self.refresh_ship_list,
                  bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
                  padx=15, pady=5).pack(side=tk.RIGHT, padx=5)

        main_frame = tk.Frame(page, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        tree_frame = tk.Frame(main_frame, bg="#ecf0f1")
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.ship_tree = ttk.Treeview(tree_frame,
                                      columns=("SoHieu", "Class", "NgayTao"),
                                      show='headings', height=22)
        self.ship_tree.heading("SoHieu", text="Số hiệu")
        self.ship_tree.heading("Class", text="Loại tàu")
        self.ship_tree.heading("NgayTao", text="Ngày tạo")

        self.ship_tree.column("SoHieu", width=200, anchor="center")
        self.ship_tree.column("Class", width=240, anchor="center")
        self.ship_tree.column("NgayTao", width=200, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.ship_tree.yview)
        self.ship_tree.configure(yscrollcommand=scrollbar.set)
        self.ship_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ship_tree.bind("<<TreeviewSelect>>", self.on_ship_select)

        btn_frame = tk.Frame(tree_frame, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, pady=8)

        tk.Button(btn_frame, text="➕ THÊM TÀU", width=12, bg="#28a745", fg="white",
                  font=("Arial", 10, "bold"), command=self.add_ship_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✏ SỬA", width=12, bg="#ffc107", fg="black",
                  font=("Arial", 10, "bold"), command=self.edit_ship_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑 XÓA", width=12, bg="#dc3545", fg="white",
                  font=("Arial", 10, "bold"), command=self.delete_ship).pack(side=tk.LEFT, padx=5)

        detail_panel = tk.Frame(main_frame, bg="white", width=340, relief="ridge", bd=2)
        detail_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        detail_panel.pack_propagate(False)

        tk.Label(detail_panel, text="CHI TIẾT TÀU", font=("Arial", 13, "bold"), bg="white").pack(pady=12)

        self.ship_img_canvas = tk.Canvas(detail_panel, width=300, height=260, bg="#eeeeee")
        self.ship_img_canvas.pack(pady=8)

        self.ship_info_label = tk.Label(detail_panel, text="", font=("Arial", 10),
                                        bg="white", wraplength=290, justify=tk.LEFT)
        self.ship_info_label.pack(pady=10, padx=15)

    # ====================== CÁC HÀM CRUD ======================

    def refresh_ship_list(self):
        for i in self.ship_tree.get_children():
            self.ship_tree.delete(i)
        self.ship_img_paths.clear()

        self.ship_img_canvas.delete("all")
        self.ship_img_canvas.create_text(145, 130, text="Chọn một tàu\nđể xem chi tiết",
                                         fill="gray", font=("Arial", 12))
        self.ship_info_label.config(text="")

        conn = get_db_connection()
        if not conn:
            messagebox.showerror("Lỗi Database", "Không thể kết nối đến cơ sở dữ liệu!")
            return

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ship_id, so_hieu, class_name, anh_dai_dien, ngay_tao
                FROM ship
                ORDER BY ngay_tao DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                item_id = self.ship_tree.insert("", tk.END, values=(
                    row[1],
                    row[2] or 'N/A',
                    row[4]
                ))
                self.ship_img_paths[item_id] = row[3]
        except Exception as e:
            messagebox.showerror("Lỗi Truy vấn", f"Không thể tải danh sách tàu:\n{str(e)}")
        finally:
            conn.close()

        self.ship_refresh_status.config(text="✅ Đã làm mới!")
        self.root.after(2000, lambda: self.ship_refresh_status.config(text=""))

    def add_ship_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Thêm tàu mới")
        dialog.geometry("450x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        self.temp_image_path = tk.StringVar()

        tk.Label(dialog, text="Số hiệu tàu (*)", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_sohieu = tk.Entry(dialog, font=("Arial", 11), width=40)
        e_sohieu.pack(padx=20, pady=2)

        # ── Combobox chọn loại tàu ──
        tk.Label(dialog, text="Loại tàu", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_class = ttk.Combobox(dialog, font=("Arial", 11), width=38,
                               values=CLASS_OPTIONS, state="readonly")
        e_class.set(CLASS_OPTIONS[0])
        e_class.pack(padx=20, pady=2)

        tk.Label(dialog, text="Ảnh đại diện", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)

        frame_path = tk.Frame(dialog)
        frame_path.pack(fill=tk.X, padx=20)

        e_anh = tk.Entry(frame_path, font=("Arial", 10), textvariable=self.temp_image_path,
                         width=30, state='readonly')
        e_anh.pack(side=tk.LEFT, padx=(0, 5))

        def browse_image():
            file_path = filedialog.askopenfilename(
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
            )
            if file_path:
                self.temp_image_path.set(file_path)

        tk.Button(frame_path, text="Chọn file...", command=browse_image).pack(side=tk.LEFT)

        def save():
            so_hieu = e_sohieu.get().strip()
            if not so_hieu:
                messagebox.showwarning("Thiếu dữ liệu", "Số hiệu tàu không được để trống!")
                return

            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO ship (so_hieu, class_name, anh_dai_dien, ngay_tao)
                        VALUES (?, ?, ?, GETDATE())
                    """, (so_hieu, e_class.get(), self.temp_image_path.get()))
                    conn.commit()
                    messagebox.showinfo("Thành công", f"Đã thêm tàu {so_hieu}!")
                    dialog.destroy()
                    self.refresh_ship_list()
                except Exception as ex:
                    messagebox.showerror("Lỗi Database", str(ex))
                finally:
                    conn.close()

        tk.Button(dialog, text="LƯU TÀU", bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                  height=2, width=20, command=save).pack(pady=30)

    def edit_ship_dialog(self):
        selected = self.ship_tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một tàu để sửa!")
            return

        item = self.ship_tree.item(selected[0])
        sohieu = item['values'][0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT class_name, anh_dai_dien FROM ship WHERE so_hieu = ?", (sohieu,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Sửa tàu: {sohieu}")
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.grab_set()

        # ── Combobox chọn loại tàu ──
        tk.Label(dialog, text="Loại tàu", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_class = ttk.Combobox(dialog, font=("Arial", 11), width=38,
                               values=CLASS_OPTIONS, state="readonly")
        current_class = row[0] or ""
        e_class.set(current_class if current_class in CLASS_OPTIONS else CLASS_OPTIONS[0])
        e_class.pack(padx=20, pady=2)

        tk.Label(dialog, text="Ảnh đại diện", font=("Arial", 10)).pack(anchor="w", padx=20, pady=5)
        e_anh = tk.Entry(dialog, font=("Arial", 11), width=40)
        e_anh.insert(0, row[1] or "")
        e_anh.pack(padx=20, pady=2)

        def save_edit():
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE ship
                        SET class_name=?, anh_dai_dien=?, ngay_cap_nhat=GETDATE()
                        WHERE so_hieu=?
                    """, (e_class.get(), e_anh.get().strip(), sohieu))
                    conn.commit()
                    messagebox.showinfo("Thành công", "Đã cập nhật tàu!")
                    dialog.destroy()
                    self.refresh_ship_list()
                except Exception as ex:
                    messagebox.showerror("Lỗi", str(ex))
                finally:
                    conn.close()

        tk.Button(dialog, text="CẬP NHẬT", bg="#ffc107", fg="black", font=("Arial", 12, "bold"),
                  height=2, width=20, command=save_edit).pack(pady=20)

    def delete_ship(self):
        selected = self.ship_tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn tàu cần xóa!")
            return

        sohieu = self.ship_tree.item(selected[0])['values'][0]
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa tàu\n{sohieu}?"):
            return

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ship WHERE so_hieu = ?", (sohieu,))
                conn.commit()
                messagebox.showinfo("Thành công", f"Đã xóa tàu {sohieu}")
                self.refresh_ship_list()
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))
            finally:
                conn.close()

    def on_ship_select(self, event):
        selected = self.ship_tree.selection()
        if not selected:
            return

        item_id = selected[0]
        values = self.ship_tree.item(item_id, "values")
        img_path = self.ship_img_paths.get(item_id, "")

        info = (f"🔢 Số hiệu   : {values[0]}\n"
                f"🚢 Loại tàu  : {values[1]}\n"
                f"📅 Ngày tạo  : {values[2]}")
        self.ship_info_label.config(text=info)

        self.ship_img_canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                img = cv2.imread(img_path)
                if img is None:
                    raise ValueError("Không đọc được ảnh")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (290, 260))
                self.tk_ship_img = ImageTk.PhotoImage(image=Image.fromarray(img))
                self.ship_img_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_ship_img)
            except Exception as e:
                self.ship_img_canvas.create_text(145, 130, text="⚠️ Lỗi load ảnh",
                                                 fill="red", font=("Arial", 12))
        else:
            self.ship_img_canvas.create_text(145, 130, text="📷 Không có ảnh đại diện",
                                             fill="gray", font=("Arial", 12))

    def refresh_database(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree_img_paths.clear()

        self.db_img_canvas.delete("all")
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh",
                                       fill="gray", font=("Arial", 12))
        self.db_info_label.config(text="")

        conn = get_db_connection()
        if not conn:
            messagebox.showerror("Lỗi Database", "Không thể kết nối đến cơ sở dữ liệu!")
            return

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT track_id, class_name, ISNULL(so_hieu_ocr, 'N/A'),
                       toc_do_tb, gio_phat_hien, ISNULL(hinh_anh_path, ''),
                       ISNULL(video_source, 'Unknown')
                FROM shiplog
                ORDER BY gio_phat_hien DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                toc_do_display = f"{row[3]:.1f}" if row[3] is not None else 'N/A'
                item_id = self.tree.insert("", tk.END, values=(
                    row[0], row[1], row[2], toc_do_display, row[4], row[6]
                ))
                self.tree_img_paths[item_id] = row[5]
        except Exception as e:
            messagebox.showerror("Lỗi Truy vấn", f"Không thể tải dữ liệu:\n{str(e)}")
        finally:
            conn.close()

        self.refresh_status.config(text="✅ Đã làm mới!")
        self.root.after(2000, lambda: self.refresh_status.config(text=""))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        img_path = self.tree_img_paths.get(item_id, "")

        info = (f"🆔 ID Tracking : {values[0]}\n"
                f"🚢 Loại tàu      : {values[1]}\n"
                f"🔢 Số hiệu (OCR) : {values[2]}\n"
                f"⚡ Tốc độ TB      : {values[3]} km/h\n"
                f"🕐 Giờ phát hiện : {values[4]}\n"
                f"📹 Nguồn video   : {values[5]}")
        self.db_info_label.config(text=info)

        self.db_img_canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                img = cv2.imread(img_path)
                if img is None:
                    raise ValueError("Không đọc được ảnh")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (290, 260))
                self.tk_db_img = ImageTk.PhotoImage(image=Image.fromarray(img))
                self.db_img_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_db_img)
            except Exception as e:
                self.db_img_canvas.create_text(145, 130, text="⚠️ Lỗi load ảnh",
                                               fill="red", font=("Arial", 12))
        else:
            self.db_img_canvas.create_text(145, 130, text="📷 Không có ảnh",
                                           fill="gray", font=("Arial", 12))

    def manual_ocr_selected_ship(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một tàu trong bảng trước!")
            return

        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        track_id_str = values[0]

        try:
            track_id = int(track_id_str)
        except ValueError:
            messagebox.showerror("Lỗi", "ID Tracking không hợp lệ!")
            return

        if hasattr(self, 'engine') and self.engine is not None:
            if track_id in self.engine.current_objects:
                self.engine.request_manual_ocr(track_id)
                messagebox.showinfo("Đã gửi", f"Đã yêu cầu OCR thủ công cho ID {track_id}.\nKết quả sẽ cập nhật sau vài giây.")
                return
            else:
                img_path = self.tree_img_paths.get(item_id, "")
                if img_path and os.path.exists(img_path):
                    try:
                        crop_img = cv2.imread(img_path)
                        if crop_img is not None:
                            self.engine.ocr_queue.put((track_id, crop_img, True))
                            messagebox.showinfo("Đã gửi", f"OCR thủ công từ ảnh lưu cho ID {track_id}.")
                            return
                    except Exception as e:
                        messagebox.showerror("Lỗi", f"Không thể đọc ảnh để OCR lại: {str(e)}")
                else:
                    messagebox.showwarning("Không có ảnh", "Không tìm thấy ảnh crop để OCR lại.")
        else:
            messagebox.showwarning("Cảnh báo", "Hệ thống giám sát chưa chạy.\nKhông thể thực hiện OCR lúc này.")

    def choose_model(self):
        p = filedialog.askopenfilename(filetypes=[("Model", "*.pt *.engine")])
        if p:
            self.model_path.set(p)

    def choose_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi")])
        if p:
            self.video_path.set(p)

    def choose_output_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.output_dir.set(p)

    def start_process(self):
        if not all([self.model_path.get(), self.video_path.get(), self.output_dir.get()]):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn đầy đủ Model, Video và Output!")
            return
        try:
            img_sz = int(self.img_size_entry.get())
            skp = int(self.skip_frame_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Image Size và Skip Frame phải là số nguyên!")
            return

        self.selected_track_id = None
        os.makedirs(self.output_dir.get(), exist_ok=True)

        self.engine = YoloTester(
            model_path=self.model_path.get(),
            input_source=self.video_path.get(),
            output_folder=self.output_dir.get(),
            conf=self.conf_val.get(),
            imgsz=img_sz,
            stride=skp,
            use_ocr=self.use_ocr_var.get()
        )

        self.thread = threading.Thread(target=self.engine.run, args=(self.update_frame,))
        self.thread.daemon = True
        self.thread.start()

    def stop_process(self):
        if hasattr(self, 'engine') and self.engine:
            self.engine.stop()

    def update_frame(self, frame, fps):
        h, w = frame.shape[:2]
        ch, cw = self.canvas_video.winfo_height(), self.canvas_video.winfo_width()
        if ch <= 0 or cw <= 0:
            return

        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        self.last_scale = scale
        self.last_offset = ((cw - nw) // 2, (ch - nh) // 2)

        img = cv2.resize(frame, (nw, nh))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.canvas_video.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=self.tk_img)

    def on_canvas_click(self, event):
        if not hasattr(self, 'engine') or not hasattr(self, 'last_scale'):
            return

        x_click = (event.x - self.last_offset[0]) / self.last_scale
        y_click = (event.y - self.last_offset[1]) / self.last_scale

        found = False
        for tid, obj in self.engine.current_objects.items():
            x1, y1, x2, y2 = obj["bbox"]
            if x1 <= x_click <= x2 and y1 <= y_click <= y2:
                self.selected_track_id = tid
                self.show_crop(obj["crop"])

                speed = obj.get("speed_kmh", 0.0)
                detail = f"🆔 ID Tracking: {tid}\n"
                if obj["ocr"] != "...":
                    detail += f"🔢 Số hiệu: {obj['ocr']}\n"
                detail += f"⚡ Tốc độ hiện tại: {speed:.1f} km/h\n"
                detail += "Đang phân tích..."

                self.detail_text.config(text=detail)
                found = True
                break

        if not found:
            self.detail_text.config(text="Không tìm thấy tàu tại vị trí click.\nClick vào bounding box để xem chi tiết.")

    def show_crop(self, img_cv):
        if img_cv is None or img_cv.size == 0:
            return
        img = cv2.resize(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB), (280, 200))
        self.tk_crop = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.detail_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_crop)

    def logout(self):
        if messagebox.askyesno("Đăng xuất", "Bạn có chắc muốn đăng xuất?"):
            self.stop_process()
            self.root.destroy()
            os.system('python login.py')

    def on_closing(self):
        self.stop_process()
        close_db_connection()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()