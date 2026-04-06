import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os
from src.views.log_view import LogView

CLASS_OPTIONS = ["speed boat", "passenger ship", "fishing boat"]

class MainView:
    def __init__(self, root, callbacks):
        self.root = root
        self.callbacks = callbacks
        self.engine = None  # ← Khởi tạo engine = None để tránh AttributeError
        self.root.title("AI Model Testing Tool - Modular Version")
        self.root.geometry("1400x900")

        self.output_dir = tk.StringVar()
        self.model_path = tk.StringVar()
        self.ocr_model_path = tk.StringVar()  # Biến lưu đường dẫn Text Model cho 2-Stage OCR
        self.video_path = tk.StringVar()
        self.tracker_path = tk.StringVar(value="bytetrack.yaml")  # Tracker file path
        self.conf_val = tk.DoubleVar(value=0.5)
        self.use_ocr_var = tk.BooleanVar(value=True)
        self.tree_img_paths = {}
        self.tracker_files = []  # Lưu danh sách file tracker

        self.last_scale = 1.0
        self.last_offset = (0, 0)
        self.tk_img = None
        self.tk_crop = None
        self.tk_db_img = None

        self.model_files = []
        self.ocr_model_files = []

        self.setup_navbar()
        self.container = tk.Frame(self.root)
        self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.frames = {}
        
        self.setup_monitoring_page()
        self.load_trackers()  # Load tracker files từ thư mục trackers
        self.setup_combobox_bindings()
        
        # Khởi tạo LogView (Nhật ký)
        self.log_view = LogView(self.container)
        self.frames["database"] = self.log_view.get_frame()
        self.log_view.refresh_button.config(command=self.callbacks["refresh_database"])
        self.log_view.manual_ocr_btn.config(command=self.callbacks["manual_ocr"])
        self.log_view.tree.bind("<<TreeviewSelect>>", self.callbacks["on_tree_select"])
        
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


    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "database":
            self.callbacks["refresh_current_page"]()

    def setup_monitoring_page(self):
        page = tk.Frame(self.container, bg="#f8f9fa")
        self.frames["monitoring"] = page
        page.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.canvas_video = tk.Canvas(page, bg="black")
        self.canvas_video.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas_video.bind("<Button-1>", self.callbacks["on_canvas_click"])

        # ────────────────────────────────────────────────────────────────
        # Right Panel - Contains Control Panel & Detail Panel stacked vertically using GRID
        # ────────────────────────────────────────────────────────────────
        right_panel = tk.Frame(page, bg="#ffffff", relief="flat", bd=0)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=8, pady=10)
        right_panel.pack_propagate(False)
        right_panel.config(width=380)
        
        # Configure grid layout for right_panel
        right_panel.grid_rowconfigure(0, weight=0)  # Control panel - no expansion
        right_panel.grid_rowconfigure(1, weight=1)  # Detail panel - fills remaining space
        right_panel.grid_columnconfigure(0, weight=1)

        # ────────────────────────────────────────────────────────────────
        # Control Panel - Redesigned & Compact Layout
        # ────────────────────────────────────────────────────────────────
        control_frame = tk.Frame(right_panel, bg="#ffffff", relief="flat", bd=0)
        control_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))
        control_frame.pack_propagate(True)

        # Header
        header = tk.Frame(control_frame, bg="#2c3e50", height=35)
        header.pack(fill=tk.X, padx=0, pady=(0, 5))
        header.pack_propagate(False)
        tk.Label(header, text="⚙️ CÔNG CỤ TEST", font=("Segoe UI", 11, "bold"), 
                 fg="white", bg="#2c3e50").pack(pady=6)

        # ════════════════════════════════════════════════════════════════
        # Section 1: Architecture (Compact)
        # ════════════════════════════════════════════════════════════════
        sec1 = tk.Frame(control_frame, bg="#f8f9fa", relief="flat")
        sec1.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(sec1, text="Kiến trúc", font=("Segoe UI", 9, "bold"), 
                 bg="#f8f9fa", fg="#2c3e50").pack(anchor="w", pady=(2, 2))
        
        # Model Row
        model_row = tk.Frame(sec1, bg="#f8f9fa")
        model_row.pack(fill=tk.X, pady=1)
        tk.Label(model_row, text="Loại:", font=("Segoe UI", 8), bg="#f8f9fa", width=8).pack(side=tk.LEFT)
        self.model_combo = ttk.Combobox(model_row, values=["YOLO"], state="readonly", width=18, font=("Segoe UI", 8))
        self.model_combo.set("YOLO")
        self.model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        
        # Tracker Row
        tracker_row = tk.Frame(sec1, bg="#f8f9fa")
        tracker_row.pack(fill=tk.X, pady=1)
        tk.Label(tracker_row, text="Tracker:", font=("Segoe UI", 8), bg="#f8f9fa", width=8).pack(side=tk.LEFT)
        self.cb_tracker = ttk.Combobox(tracker_row, state="readonly", width=18, font=("Segoe UI", 8))
        self.cb_tracker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        # ════════════════════════════════════════════════════════════════
        # Section 2: File Configuration (ComboBox Layout)
        # ════════════════════════════════════════════════════════════════
        sec2 = tk.Frame(control_frame, bg="#f8f9fa", relief="flat")
        sec2.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(sec2, text="File & Thư mục", font=("Segoe UI", 9, "bold"), 
                 bg="#f8f9fa", fg="#2c3e50").pack(anchor="w", pady=(2, 3))

        # Helper function to create a file row with ComboBox (label | combobox | browse button)
        def create_file_row_combo(parent, icon, label_text, browse_cmd):
            row = tk.Frame(parent, bg="#f8f9fa")
            row.pack(fill=tk.X, pady=1)
            row.grid_columnconfigure(1, weight=1)
            
            tk.Label(row, text=f"{icon} {label_text}", font=("Segoe UI", 8), 
                    bg="#f8f9fa", fg="#2c3e50", width=12, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 5))
            
            combo = ttk.Combobox(row, font=("Segoe UI", 7), width=16, state="readonly")
            combo.grid(row=0, column=1, sticky="ew", padx=(0, 3))
            
            tk.Button(row, text="...", command=browse_cmd, font=("Segoe UI", 7, "bold"), 
                     width=3, relief="flat", bg="#ecf0f1", fg="#2c3e50").grid(row=0, column=2)
            
            return combo

        # Helper function to create Output row with Entry widget
        def create_file_row_entry(parent, icon, label_text, browse_cmd):
            row = tk.Frame(parent, bg="#f8f9fa")
            row.pack(fill=tk.X, pady=1)
            row.grid_columnconfigure(1, weight=1)
            
            tk.Label(row, text=f"{icon} {label_text}", font=("Segoe UI", 8), 
                    bg="#f8f9fa", fg="#2c3e50", width=12, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 5))
            
            entry = tk.Entry(row, font=("Segoe UI", 7), relief="solid", bd=1)
            entry.grid(row=0, column=1, sticky="ew", padx=(0, 3))
            
            tk.Button(row, text="...", command=browse_cmd, font=("Segoe UI", 7, "bold"), 
                     width=3, relief="flat", bg="#ecf0f1", fg="#2c3e50").grid(row=0, column=2)
            
            return entry

        self.model_combo_file = create_file_row_combo(sec2, "🗂️", "Model", self.browse_model_files)
        self.ocr_model_combo = create_file_row_combo(sec2, "🔤", "Text (OCR)", self.browse_ocr_model_files)
        self.video_combo = create_file_row_combo(sec2, "🎬", "Video", self.browse_video_files)
        self.output_dir_entry = create_file_row_entry(sec2, "📂", "Output", self.choose_output_folder)

        # ════════════════════════════════════════════════════════════════
        # Section 3: Test Parameters (Compact Grid)
        # ════════════════════════════════════════════════════════════════
        sec3 = tk.Frame(control_frame, bg="#f8f9fa", relief="flat")
        sec3.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(sec3, text="Tham số", font=("Segoe UI", 9, "bold"), 
                 bg="#f8f9fa", fg="#2c3e50").pack(anchor="w", pady=(2, 3))

        sec3.grid_columnconfigure(1, weight=1)

        # imgsz Row
        row1 = tk.Frame(sec3, bg="#f8f9fa")
        row1.pack(fill=tk.X, pady=1)
        row1.grid_columnconfigure(1, weight=0)
        tk.Label(row1, text="imgsz:", font=("Segoe UI", 8), bg="#f8f9fa", width=8).grid(row=0, column=0, sticky="w")
        self.img_size_entry = tk.Entry(row1, font=("Segoe UI", 8), relief="solid", bd=1, width=7)
        self.img_size_entry.insert(0, "640")
        self.img_size_entry.grid(row=0, column=1, sticky="w", padx=(0, 6))
        
        tk.Label(row1, text="stride:", font=("Segoe UI", 8), bg="#f8f9fa", width=7).grid(row=0, column=2, sticky="w")
        self.skip_frame_entry = tk.Entry(row1, font=("Segoe UI", 8), relief="solid", bd=1, width=5)
        self.skip_frame_entry.insert(0, "3")
        self.skip_frame_entry.grid(row=0, column=3, sticky="w")

        # Confidence Slider
        row2 = tk.Frame(sec3, bg="#f8f9fa")
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="conf:", font=("Segoe UI", 8), bg="#f8f9fa", width=8).pack(side=tk.LEFT)
        tk.Scale(row2, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                 variable=self.conf_val, bg="#f8f9fa", fg="#2c3e50", highlightthickness=0, length=120).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.conf_label = tk.Label(row2, text="0.50", font=("Segoe UI", 8), bg="#f8f9fa", width=4)
        self.conf_label.pack(side=tk.LEFT)
        
        def update_conf_label(val):
            self.conf_label.config(text=f"{float(val):.2f}")
        self.conf_val.trace("w", lambda n, i, m: update_conf_label(self.conf_val.get()))

        # OCR Checkbox
        row3 = tk.Frame(sec3, bg="#f8f9fa")
        row3.pack(fill=tk.X, pady=2)
        tk.Checkbutton(row3, text="🔤 Bật 2-Stage OCR", font=("Segoe UI", 8), 
                      variable=self.use_ocr_var, bg="#f8f9fa", fg="#2c3e50", 
                      selectcolor="#f8f9fa", activebackground="#f8f9fa", activeforeground="#2c3e50").pack(anchor="w")

        # ════════════════════════════════════════════════════════════════
        # Action Buttons (Compact & Modern)
        # ════════════════════════════════════════════════════════════════
        btn_frame = tk.Frame(control_frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X, padx=12, pady=(4, 8))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        # Start button
        start_btn = tk.Button(btn_frame, text="▶ BẮT ĐẦU", bg="#27ae60", fg="white", 
                             font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                             command=self.callbacks["start_process"])
        start_btn.grid(row=0, column=0, sticky="nsew", padx=(0, 3), pady=2)
        
        # Stop button
        stop_btn = tk.Button(btn_frame, text="⏹ DỪNG", bg="#e74c3c", fg="white", 
                            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                            command=self.callbacks["stop_process"])
        stop_btn.grid(row=0, column=1, sticky="nsew", padx=(3, 0), pady=2)

        # Hover effects
        def on_btn_enter(btn, color):
            def handler(e): btn.config(bg=color)
            return handler
        def on_btn_leave(btn, color):
            def handler(e): btn.config(bg=color)
            return handler
        
        start_btn.bind("<Enter>", on_btn_enter(start_btn, "#229954"))
        start_btn.bind("<Leave>", on_btn_leave(start_btn, "#27ae60"))
        stop_btn.bind("<Enter>", on_btn_enter(stop_btn, "#c0392b"))
        stop_btn.bind("<Leave>", on_btn_leave(stop_btn, "#e74c3c"))

        # ════════════════════════════════════════════════════════════════
        # Detail Panel (Right side - Ship Info) - Stacked below Control Panel
        # ════════════════════════════════════════════════════════════════
        self.detail_frame = tk.Frame(right_panel, bg="#ffffff", relief="flat", bd=0)
        self.detail_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.detail_frame.pack_propagate(True)

        detail_header = tk.Frame(self.detail_frame, bg="#34495e", height=45)
        detail_header.pack(fill=tk.X, padx=0, pady=(0, 8))
        detail_header.pack_propagate(False)
        tk.Label(detail_header, text="🚢 CHI TIẾT TÀU", font=("Segoe UI", 11, "bold"), 
                 bg="#34495e", fg="white").pack(pady=10)

        self.detail_canvas = tk.Canvas(self.detail_frame, width=340, height=180, bg="#e8e8e8", relief="flat", bd=0)
        self.detail_canvas.pack(pady=(0, 8), fill=tk.BOTH, expand=True, padx=10)
        
        self.detail_text = tk.Label(self.detail_frame, text="👆 Click vào tàu trên video...",
                                    font=("Segoe UI", 9), wraplength=340, justify=tk.LEFT, 
                                    bg="#ffffff", fg="#555555", pady=8, padx=10)
        self.detail_text.pack(fill=tk.X)

    # ==================== MODEL FILES - ComboBox ====================
    def browse_model_files(self):
        """Browse folder and populate Model ComboBox with .pt files"""
        folder = filedialog.askdirectory(title="Chọn thư mục chứa model")
        if not folder: 
            return
        
        self._model_folder = folder
        model_files = [f for f in os.listdir(folder) if f.lower().endswith('.pt')]
        if model_files:
            self.model_combo_file['values'] = model_files
            self.model_combo_file.current(0)
            # Store selected file path
            selected_file = model_files[0]
            self.model_path.set(os.path.join(folder, selected_file))
        else:
            messagebox.showwarning("Thông báo", "Không tìm thấy file .pt trong thư mục")
            self.model_combo_file['values'] = []

    # ==================== OCR MODEL FILES - ComboBox ====================
    def browse_ocr_model_files(self):
        """Browse folder and populate OCR Model ComboBox with .pt files"""
        folder = filedialog.askdirectory(title="Chọn thư mục chứa model Text Detection")
        if not folder: 
            return
        
        self._ocr_folder = folder
        ocr_files = [f for f in os.listdir(folder) if f.lower().endswith('.pt')]
        if ocr_files:
            self.ocr_model_combo['values'] = ocr_files
            self.ocr_model_combo.current(0)
            # Store selected file path
            selected_file = ocr_files[0]
            self.ocr_model_path.set(os.path.join(folder, selected_file))
        else:
            messagebox.showwarning("Thông báo", "Không tìm thấy file .pt trong thư mục")
            self.ocr_model_combo['values'] = []

    # Bind ComboBox selection changes to update model_path and ocr_model_path
    def setup_combobox_bindings(self):
        """Setup bindings for ComboBox selection changes"""
        def on_model_selected(event):
            selected = self.model_combo_file.get()
            if selected and self.model_combo_file.cget('values'):
                # Get the folder from current selections
                if hasattr(self, '_model_folder'):
                    self.model_path.set(os.path.join(self._model_folder, selected))
        
        def on_ocr_selected(event):
            selected = self.ocr_model_combo.get()
            if selected and self.ocr_model_combo.cget('values'):
                if hasattr(self, '_ocr_folder'):
                    self.ocr_model_path.set(os.path.join(self._ocr_folder, selected))
        
        def on_video_selected(event):
            selected = self.video_combo.get()
            if selected and self.video_combo.cget('values'):
                if hasattr(self, '_video_folder'):
                    self.video_path.set(os.path.join(self._video_folder, selected))
        
        def on_tracker_selected(event):
            self.on_tracker_selected(event)
        
        self.model_combo_file.bind("<<ComboboxSelected>>", on_model_selected)
        self.ocr_model_combo.bind("<<ComboboxSelected>>", on_ocr_selected)
        self.video_combo.bind("<<ComboboxSelected>>", on_video_selected)
        self.cb_tracker.bind("<<ComboboxSelected>>", on_tracker_selected)

    # ==================== TRACKER FILES - Auto Load ====================
    def load_trackers(self):
        """Quét thư mục trackers và load các file .yaml/.yml vào Combobox"""
        try:
            from pathlib import Path
            
            # Tìm thư mục trackers
            tracker_dir = Path(__file__).parent.parent / "trackers"
            
            if not tracker_dir.exists():
                print(f"⚠️ Thư mục trackers không tìm thấy: {tracker_dir}")
                self.cb_tracker['values'] = ["None"]
                self.cb_tracker.set("None")
                return
            
            # Lọc file .yaml và .yml
            yaml_files = sorted(list(tracker_dir.glob("*.yaml")) + list(tracker_dir.glob("*.yml")))
            
            if not yaml_files:
                print("⚠️ Không có file .yaml hoặc .yml trong thư mục trackers")
                self.cb_tracker['values'] = ["None"]
                self.cb_tracker.set("None")
                return
            
            # Lưu đường dẫn đầy đủ và hiển thị tên file
            self.tracker_files = yaml_files
            tracker_names = [f.name for f in yaml_files]  # Chỉ lấy tên file
            
            self.cb_tracker['values'] = tracker_names
            self.cb_tracker.set(tracker_names[0])  # Set mặc định file đầu tiên
            
            # Cập nhật tracker_path với đường dẫn đầy đủ
            self.tracker_path.set(str(yaml_files[0]))
            
            print(f"✅ Đã load {len(tracker_names)} tracker file: {tracker_names}")
            
        except Exception as e:
            print(f"❌ Lỗi load tracker files: {e}")
            self.cb_tracker['values'] = ["None"]
            self.cb_tracker.set("None")
    
    def on_tracker_selected(self, event=None):
        """Xử lý khi người dùng chọn tracker từ Combobox"""
        selected_name = self.cb_tracker.get()
        
        if selected_name == "None" or not self.tracker_files:
            self.tracker_path.set("bytetrack.yaml")
            return
        
        # Tìm file tương ứng
        for f in self.tracker_files:
            if f.name == selected_name:
                self.tracker_path.set(str(f))
                break

    # ==================== VIDEO FILES - ComboBox ====================
    def browse_video_files(self):
        """Browse folder and populate Video ComboBox with video files"""
        folder = filedialog.askdirectory(title="Chọn thư mục chứa video")
        if not folder: 
            return
        
        video_ext = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm')
        video_files = [f for f in os.listdir(folder) if f.lower().endswith(video_ext)]
        
        if video_files:
            self._video_folder = folder
            self.video_combo['values'] = video_files
            self.video_combo.current(0)
            # Store selected file path
            selected_file = video_files[0]
            self.video_path.set(os.path.join(folder, selected_file))
        else:
            messagebox.showwarning("Thông báo", "Không tìm thấy file video trong thư mục")
            self.video_combo['values'] = []

    # ==================== OUTPUT ====================
    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục lưu output")
        if not folder: 
            return
        self.output_dir.set(folder)
        self.output_dir_entry.delete(0, tk.END)
        self.output_dir_entry.insert(0, folder)

    # ==================== WRAPPER METHODS CHO LOG_VIEW ====================
    def refresh_database_ui(self, rows):
        """Wrapper gọi đến log_view"""
        self.log_view.refresh_database_ui(rows)
    
    def show_db_info(self, info, img_path):
        """Wrapper gọi đến log_view"""
        self.log_view.show_db_info(info, img_path)

    @property
    def tree(self):
        """Shortcut để truy cập tree từ log_view"""
        return self.log_view.tree
    
    @property
    def ship_history_tree(self):
        """Shortcut để truy cập ship_history_tree từ log_view"""
        return self.log_view.ship_history_tree
    
    @property
    def refresh_status(self):
        """Shortcut để truy cập refresh_status từ log_view"""
        return self.log_view.refresh_status
    
    @refresh_status.setter
    def refresh_status(self, value):
        """Setter cho refresh_status"""
        self.log_view.refresh_status.config(text=value)

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
        img = cv2.resize(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB), (330, 170))
        self.tk_crop = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.detail_canvas.create_image(170, 85, anchor=tk.CENTER, image=self.tk_crop)

    def show_detail_text(self, text):
        self.detail_text.config(text=text)

    def show_warning(self, title, msg):
        messagebox.showwarning(title, msg)

    def show_error(self, title, msg):
        messagebox.showerror(title, msg)

    def show_info(self, title, msg):
        messagebox.showinfo(title, msg)

    def ask_yesno(self, title, msg):
        return messagebox.askyesno(title, msg)

    def on_ship_action_click(self, event):
        region = self.ship_tree.identify("region", event.x, event.y)
        column = self.ship_tree.identify("column", event.x, event.y)
        if region == "cell" and column == "#4":
            item = self.ship_tree.identify("item", event.x, event.y)
            if item:
                x_rel = event.x - self.ship_tree.bbox(item, column)[0]
                col_width = self.ship_tree.column(column, "width")
                mid_point = col_width // 2
                if x_rel < mid_point:
                    self.callbacks["edit_ship_dialog"]()
                else:
                    self.callbacks["delete_ship"]()