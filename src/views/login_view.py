import tkinter as tk
from tkinter import messagebox

class LoginView:
    def __init__(self, root, on_login_attempt_callback):
        self.root = root
        self.root.title("Ship_Detection")
        self.root.geometry("380x420")
        self.root.configure(bg="#f0f2f5")
        self.on_login_attempt = on_login_attempt_callback

        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.frame = tk.Frame(self.root, bg="white", bd=0, relief="flat", padx=30, pady=30)
        self.frame.place(relx=0.5, rely=0.5, anchor="center", width=320, height=360)

        tk.Label(self.frame, text="ĐĂNG NHẬP", font=("Segoe UI", 18, "bold"),
                 bg="white", fg="#1c1e21").pack(pady=(0, 20))

        tk.Label(self.frame, text="Tên đăng nhập", font=("Segoe UI", 10),
                 bg="white", fg="#606770").pack(anchor="w")
        self.ent_user = tk.Entry(self.frame, font=("Segoe UI", 11), bg="#f5f6f7",
                                 relief="flat", bd=0, highlightthickness=1, highlightbackground="#dddfe2")
        self.ent_user.pack(fill="x", ipady=8, pady=(5, 15))
        self.ent_user.focus_set()

        tk.Label(self.frame, text="Mật khẩu", font=("Segoe UI", 10),
                 bg="white", fg="#606770").pack(anchor="w")

        self.pw_container = tk.Frame(self.frame, bg="#f5f6f7", highlightthickness=1, highlightbackground="#dddfe2")
        self.pw_container.pack(fill="x")

        self.ent_pass = tk.Entry(self.pw_container, font=("Segoe UI", 11), bg="#f5f6f7",
                                 relief="flat", bd=0, show="*")
        self.ent_pass.pack(side="left", fill="x", expand=True, ipady=8, padx=5)

        self.btn_show = tk.Label(self.pw_container, text="👁", font=("Arial", 12),
                                 bg="#f5f6f7", fg="#606770", cursor="hand2")
        self.btn_show.pack(side="right", padx=10)
        self.btn_show.bind("<Button-1>", self.toggle_password)

        self.btn_login = tk.Button(self.frame, text="Đăng nhập", font=("Segoe UI", 12, "bold"),
                                   bg="#007bff", fg="white", relief="flat", bd=0,
                                   cursor="hand2", command=self._trigger_login)
        self.btn_login.pack(fill="x", ipady=10, pady=(25, 10))

        self.btn_login.bind("<Enter>", lambda e: self.btn_login.configure(bg="#0056b3"))
        self.btn_login.bind("<Leave>", lambda e: self.btn_login.configure(bg="#007bff"))

        self.root.bind('<Return>', lambda event: self._trigger_login())

    def toggle_password(self, event=None):
        if self.ent_pass.cget('show') == '*':
            self.ent_pass.config(show='')
            self.btn_show.config(text="🔒", fg="#007bff")
        else:
            self.ent_pass.config(show='*')
            self.btn_show.config(text="👁", fg="#606770")

    def _trigger_login(self):
        username = self.ent_user.get().strip()
        password = self.ent_pass.get()
        self.on_login_attempt(username, password)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def close(self):
        self.root.destroy()