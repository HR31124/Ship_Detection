import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk
import os


class LogView:
    """Giao diện Nhật ký phát hiện tàu"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.frame = tk.Frame(parent_frame, bg="#ecf0f1")
        self.frame.grid(row=0, column=0, sticky="nsew")
        
        self.tree_img_paths = {}
        self.tk_db_img = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Khởi tạo giao diện Nhật ký"""
        header_frame = tk.Frame(self.frame, bg="#ecf0f1")
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(header_frame, text="NHẬT KÝ PHÁT HIỆN", font=("Arial", 18, "bold"), bg="#ecf0f1").pack(side=tk.LEFT)
        
        self.refresh_status = tk.Label(header_frame, text="", fg="#3498db", bg="#ecf0f1", font=("Arial", 10, "italic"))
        self.refresh_status.pack(side=tk.RIGHT, padx=10)
        
        # Nút làm mới sẽ được connection tới từ main_controller
        self.refresh_button = tk.Button(header_frame, text="🔄 Làm mới (F5)",
                  bg="#3498db", fg="white", font=("Arial", 11, "bold"), padx=15, pady=5, relief="flat", cursor="hand2")
        self.refresh_button.pack(side=tk.RIGHT)
        
        main_frame = tk.Frame(self.frame, bg="#ecf0f1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        # Phần Treeview
        tree_frame = tk.Frame(main_frame, bg="#ecf0f1")
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Class", "SoHieuOCR", "TocDo", "Gio", "Video"), 
                                 show='headings', height=20)
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
        
        # Phần ảnh và info bên phải
        img_panel = tk.Frame(main_frame, bg="white", width=320, relief="ridge", bd=2)
        img_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        img_panel.pack_propagate(False)
        
        tk.Label(img_panel, text="🚢 ẢNH TÀU", font=("Arial", 13, "bold"), bg="white").pack(pady=12)
        
        self.db_img_canvas = tk.Canvas(img_panel, width=290, height=260, bg="#dddddd")
        self.db_img_canvas.pack(pady=5, padx=10)
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh", fill="gray", font=("Arial", 12))
        
        self.db_info_label = tk.Label(img_panel, text="", font=("Arial", 10), bg="white", wraplength=290, justify=tk.LEFT)
        self.db_info_label.pack(pady=8, padx=10)
        
        btn_frame = tk.Frame(img_panel, bg="white")
        btn_frame.pack(pady=12)
        
        self.manual_ocr_btn = tk.Button(btn_frame, text="⚡ OCR Thủ công", bg="#27ae60", fg="white", 
                  font=("Arial", 10, "bold"), width=15, height=2)
        self.manual_ocr_btn.pack(side=tk.LEFT, padx=5)
        
        # Hidden ship_history_tree for load_ship_history functionality
        self.ship_history_tree = ttk.Treeview(self.frame, columns=("Gio", "TocDo", "SoHieu", "Video"), show='headings', height=5)
        self.ship_history_tree.heading("Gio", text="Giờ phát hiện")
        self.ship_history_tree.heading("TocDo", text="Tốc độ TB (km/h)")
        self.ship_history_tree.heading("SoHieu", text="Số hiệu (OCR)")
        self.ship_history_tree.heading("Video", text="Nguồn video")
    
    def refresh_database_ui(self, rows):
        """Cập nhật dữ liệu lên Treeview"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree_img_paths.clear()
        self.db_img_canvas.delete("all")
        self.db_img_canvas.create_text(145, 130, text="Chọn một hàng\nđể xem ảnh", fill="gray", font=("Arial", 12))
        self.db_info_label.config(text="")
        
        for row in rows:
            toc_do_display = f"{row[3]:.1f}" if row[3] is not None else 'N/A'
            item_id = self.tree.insert("", tk.END, values=(row[0], row[1], row[2], toc_do_display, row[4], row[6]))
            self.tree_img_paths[item_id] = row[5]
    
    def show_db_info(self, info, img_path):
        """Hiển thị thông tin và ảnh của tàu"""
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
    
    def get_frame(self):
        """Trả về frame để thêm vào container"""
        return self.frame
