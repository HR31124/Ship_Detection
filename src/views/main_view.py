# src/views/main_view.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os

CLASS_OPTIONS = ["speed boat", "passenger ship", "fishing boat"]

class MainView:
    def __init__(self, root, callbacks):
        self.root = root
        self.callbacks = callbacks
        self.root.title("Hệ thống Giám sát Tàu biển - YOLO & OCR")
        self.root.geometry("1400x900")

        self.output_dir = tk.StringVar()
        self.model_path = tk.StringVar()
        self.video_path = tk.StringVar()
        self.conf_val = tk.DoubleVar(value=0.5)
        self.use_ocr_var = tk.BooleanVar(value=True)
        self.tree_img_paths = {}
        self.ship_img_paths = {}

        self.last_scale = 1.0
        self.last_offset = (0, 0)
        self.tk_img = None
        self.tk_crop = None
        self.tk_db_img = None
        self.tk_ship_img = None

        self.setup_navbar()
        self.container = tk.Frame(self.root)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.frames = {}
        self.setup_monitoring_page()
        self.setup_database_page()
        self.setup_ship_management_page()
        self.show_frame("monitoring")

        self.root.bind("<F5>", lambda e: self.callbacks["refresh_current_page"]())
        self.root.protocol("WM_DELETE_WINDOW", self.callbacks["on_closing"])

    def setup_navbar(self):
        navbar = tk.Frame(self.root, bg="#2c3e50", height=50)
        navbar.pack(side=tk.TOP, fill=tk.X)
        nav_style = {"bg": "#2c3e50", "fg": "white", "font": ("Arial", 11, "bold"),
                     "relief": "flat", "activebackground": "#34495e",
                     "activeforeground": "white", "padx": 20}
        tk.Button(navbar, text="🏠 Hệ thống giám sát", **nav_style,
                  command=lambda: self.show_frame("monitoring")).pack(side=tk.LEFT)
        tk.Button(navbar, text="📊 Nhật ký phát hiện", **nav_style,
                  command=lambda: self.show_frame("database")).pack(side=tk.LEFT)
        tk.Button(navbar, text="🚢 Quản lý tàu", **nav_style,
                  command=lambda: self.show_frame("ship_management")).pack(side=tk.LEFT)
        tk.Button(navbar, text="🚪 Đăng xuất", **nav_style,
                  command=self.callbacks["logout"]).pack(side=tk.RIGHT)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name in ["database", "ship_management"]:
            self.callbacks["refresh_current_page"]()

    def setup_monitoring_page(self):
        page = tk.Frame(self.container, bg="white")
        self.frames["monitoring"] = page
        page.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        control_frame = tk.Frame(page, bg="#f0f0f0", width=350)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        tk.Label(control_frame, text="BẢNG ĐIỀU KHIỂN", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

        tk.Button(control_frame, text="📁 Chọn Model", command=self.callbacks["choose_model"]).pack(fill=tk.X, pady=5)
        tk.Label(control_frame, textvariable=self.model_path, fg="blue", font=("Arial", 9), wraplength=300, bg="#f0f0f0").pack()
        tk.Button(control_frame, text="🎬 Chọn Video", command=self.callbacks["choose_video"]).pack(fill=tk.X, pady=5)
        tk.Label(control_frame, textvariable=self.video_path, fg="blue", font=("Arial", 9), wraplength=300, bg="#f0f0f0").pack()
        tk.Button(control_frame, text="📂 Chọn Output Folder", command=self.callbacks["choose_output_folder"]).pack(fill=tk.X, pady=5)
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
                  height=2, command=self.callbacks["start_process"]).pack(fill=tk.X, pady=5)
        tk.Button(control_frame, text="⏹ DỪNG", bg="#c0392b", fg="white",
                  command=self.callbacks["stop_process"]).pack(fill=tk.X)

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
        self.canvas_video.bind("<Button-1>", self.callbacks["on_canvas_click"])

    def setup_database_page(self):
        page = tk.Frame(self.container, bg="#ecf0f1")
        self.frames["database"] = page
        page.grid(row=0, column=0, sticky="nsew")
        header_frame = tk.Frame(page, bg="#ecf0f1")
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        tk.Label(header_frame, text="NHẬT KÝ PHÁT HIỆN", font=("Arial", 18, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)
        self.refresh_status = tk.Label(header_frame, text="", fg="#27ae60", bg="#ecf0f1", font=("Arial", 10, "italic"))
        self.refresh_status.pack(side=tk.RIGHT, padx=10)
        tk.Button(header_frame, text="🔄 Làm mới (F5)", command=self.callbacks["refresh_database"],
                  bg="#27ae60", fg="white", font=("Arial", 11, "bold"), padx=15, pady=5, relief="flat", cursor="hand2").pack(side=tk.RIGHT)
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
        for col, w in zip(["ID","Class","SoHieuOCR","TocDo","Gio","Video"], [100,140,130,120,160,180]):
            self.tree.column(col, anchor=tk.CENTER, width=w)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.callbacks["on_tree_select"])
        img_panel = tk.Frame(main_frame, bg="white", width=320, relief="ridge", bd=2)
        img_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        img_panel.pack_propagate(False)
        tk.Label(img_panel, text="🚢 ẢNH TÀU", font=("Arial", 13, "bold"), bg="white").pack(pady=12)
        self.db_img_canvas = tk.Canvas(img_panel, width=290, height=260, bg="#dddddd")
        self.db_img_canvas.pack(pady=5, padx=10)
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh", fill="gray", font=("Arial", 12))
        self.db_info_label = tk.Label(img_panel, text="", font=("Arial", 10), bg="white", wraplength=290, justify=tk.LEFT)
        self.db_info_label.pack(pady=8, padx=10)

        # === 2 NÚT OCR RIÊNG BIỆT ===
        btn_frame = tk.Frame(img_panel, bg="white")
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text="📝 OCR Thủ công", bg="#e67e22", fg="white", font=("Arial", 10, "bold"),
                  width=15, height=2, command=self.callbacks["manual_ocr_hand"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⚡ OCR Tự động", bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                  width=15, height=2, command=self.callbacks["manual_ocr_auto"]).pack(side=tk.LEFT, padx=5)

    def setup_ship_management_page(self):
        page = tk.Frame(self.container, bg="#ecf0f1")
        self.frames["ship_management"] = page
        page.grid(row=0, column=0, sticky="nsew")

        header_frame = tk.Frame(page, bg="#ecf0f1")
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        tk.Label(header_frame, text="🚢 QUẢN LÝ TÀU", font=("Arial", 18, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)
        
        self.ship_refresh_status = tk.Label(header_frame, text="", fg="#27ae60", bg="#ecf0f1", font=("Arial", 10, "italic"))
        self.ship_refresh_status.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(header_frame, text="🔄 Làm mới", command=self.callbacks["refresh_ship_list"],
                  bg="#27ae60", fg="white", font=("Arial", 11, "bold"), padx=15, pady=5).pack(side=tk.RIGHT, padx=5)

        main_frame = tk.Frame(page, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        left_frame = tk.Frame(main_frame, bg="#ecf0f1")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.ship_tree = ttk.Treeview(left_frame, columns=("SoHieu", "Class", "NgayTao"), show='headings', height=22)
        self.ship_tree.heading("SoHieu", text="Số hiệu")
        self.ship_tree.heading("Class", text="Loại tàu")
        self.ship_tree.heading("NgayTao", text="Ngày tạo")
        
        for col, w in zip(["SoHieu","Class","NgayTao"], [200,200,180]):
            self.ship_tree.column(col, width=w, anchor="center")
            
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.ship_tree.yview)
        self.ship_tree.configure(yscrollcommand=scrollbar.set)
        self.ship_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.ship_tree.bind("<<TreeviewSelect>>", self.callbacks["on_ship_select"])

        btn_frame = tk.Frame(left_frame, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, pady=8)
        tk.Button(btn_frame, text="➕ THÊM TÀU", width=12, bg="#28a745", fg="white",
                  font=("Arial", 10, "bold"), command=self.callbacks["add_ship_dialog"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✏ SỬA", width=12, bg="#ffc107", fg="black",
                  font=("Arial", 10, "bold"), command=self.callbacks["edit_ship_dialog"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑 XÓA", width=12, bg="#dc3545", fg="white",
                  font=("Arial", 10, "bold"), command=self.callbacks["delete_ship"]).pack(side=tk.LEFT, padx=5)

        right_panel = tk.Frame(main_frame, bg="#ecf0f1", width=420)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(20, 0))
        right_panel.pack_propagate(False) 

        self.detail_container = tk.LabelFrame(right_panel, text=" 🔍 Thông tin chi tiết ", 
                                             font=("Arial", 12, "bold"), bg="white", relief="ridge", bd=2)
        self.detail_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.ship_img_canvas = tk.Canvas(self.detail_container, width=380, height=240, bg="#eeeeee", highlightthickness=0)
        self.ship_img_canvas.pack(pady=10, padx=10)
        self.ship_img_canvas.create_text(190, 120, text="Chọn một tàu\nđể xem ảnh", fill="gray", font=("Arial", 10))

        self.ship_info_label = tk.Label(self.detail_container, text="", font=("Arial", 10),
                                        bg="white", wraplength=380, justify=tk.LEFT)
        self.ship_info_label.pack(fill=tk.X, pady=5, padx=15)

        self.history_container = tk.LabelFrame(right_panel, text=" 📜 Lịch sử phát hiện ", 
                                              font=("Arial", 12, "bold"), bg="white", relief="ridge", bd=2)
        self.history_container.pack(fill=tk.BOTH, expand=True)

        self.ship_history_tree = ttk.Treeview(self.history_container,
                                              columns=("ThoiGian", "TocDo", "OCR", "Video"),
                                              show='headings')
        
        self.ship_history_tree.heading("ThoiGian", text="Thời gian")
        self.ship_history_tree.heading("TocDo", text="Tốc độ")
        self.ship_history_tree.heading("OCR", text="OCR")
        self.ship_history_tree.heading("Video", text="Video")

        self.ship_history_tree.column("ThoiGian", width=130, anchor="center")
        self.ship_history_tree.column("TocDo", width=70, anchor="center")
        self.ship_history_tree.column("OCR", width=80, anchor="center")
        self.ship_history_tree.column("Video", width=100, anchor="center")

        hist_scroll = ttk.Scrollbar(self.history_container, orient="vertical", command=self.ship_history_tree.yview)
        self.ship_history_tree.configure(yscrollcommand=hist_scroll.set)
        
        self.ship_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0,5))

    # ==================== CÁC HÀM HIỂN THỊ ====================
    def update_frame(self, frame, fps):
        h, w = frame.shape[:2]
        ch, cw = self.canvas_video.winfo_height(), self.canvas_video.winfo_width()
        if ch <= 0 or cw <= 0: return
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        self.last_scale = scale
        self.last_offset = ((cw - nw) // 2, (ch - nh) // 2)
        img = cv2.resize(frame, (nw, nh))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.canvas_video.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=self.tk_img)

    def show_crop(self, img_cv):
        if img_cv is None or img_cv.size == 0: return
        img = cv2.resize(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB), (280, 200))
        self.tk_crop = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.detail_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_crop)

    def refresh_database_ui(self, rows):
        for i in self.tree.get_children(): self.tree.delete(i)
        self.tree_img_paths.clear()
        self.db_img_canvas.delete("all")
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh", fill="gray", font=("Arial", 12))
        self.db_info_label.config(text="")
        for row in rows:
            toc_do_display = f"{row[3]:.1f}" if row[3] is not None else 'N/A'
            item_id = self.tree.insert("", tk.END, values=(row[0], row[1], row[2], toc_do_display, row[4], row[6]))
            self.tree_img_paths[item_id] = row[5]

    def refresh_ship_list_ui(self, rows):
        for i in self.ship_tree.get_children(): self.ship_tree.delete(i)
        self.ship_img_paths.clear()
        self.ship_img_canvas.delete("all")
        self.ship_img_canvas.create_text(145, 130, text="Chọn một tàu\nđể xem chi tiết", fill="gray", font=("Arial", 12))
        self.ship_info_label.config(text="")
        for row in rows:
            item_id = self.ship_tree.insert("", tk.END, values=(row[1], row[2] or 'N/A', row[4]))
            self.ship_img_paths[item_id] = row[3]

    def show_detail_text(self, text):
        self.detail_text.config(text=text)

    def show_db_info(self, info, img_path):
        self.db_info_label.config(text=info)
        self.db_img_canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (290, 260))
                self.tk_db_img = ImageTk.PhotoImage(image=Image.fromarray(img))
                self.db_img_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_db_img)
            except:
                self.db_img_canvas.create_text(145, 130, text="⚠️ Lỗi load ảnh", fill="red", font=("Arial", 12))
        else:
            self.db_img_canvas.create_text(145, 130, text="📷 Không có ảnh", fill="gray", font=("Arial", 12))

    def show_ship_info(self, info, img_path):
        self.ship_info_label.config(text=info)
        self.ship_img_canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (300, 260))
                self.tk_ship_img = ImageTk.PhotoImage(image=Image.fromarray(img))
                self.ship_img_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_ship_img)
            except:
                self.ship_img_canvas.create_text(145, 130, text="⚠️ Lỗi load ảnh", fill="red", font=("Arial", 12))
        else:
            self.ship_img_canvas.create_text(145, 130, text="📷 Không có ảnh đại diện", fill="gray", font=("Arial", 12))

    def show_warning(self, title, msg):
        messagebox.showwarning(title, msg)

    def show_error(self, title, msg):
        messagebox.showerror(title, msg)

    def show_info(self, title, msg):
        messagebox.showinfo(title, msg)

    def ask_yesno(self, title, msg):
        return messagebox.askyesno(title, msg)