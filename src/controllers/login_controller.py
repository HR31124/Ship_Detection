# src/controllers/login_controller.py
from tkinter import Tk
from src.views.login_view import LoginView
from src.utils.connect import get_db_connection, release_connection   # ← ĐÃ SỬA
from src.controllers.main_controller import MainController

class LoginController:
    def __init__(self):
        self.root = Tk()
        self.view = LoginView(self.root, self.handle_login_attempt)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def handle_login_attempt(self, username: str, password: str):
        if not username or not password:
            self.view.show_warning("Chú ý", "Vui lòng nhập đầy đủ thông tin!")
            return

        conn = get_db_connection()
        if not conn:
            self.view.show_error("Lỗi hệ thống", "Không thể kết nối đến cơ sở dữ liệu!")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, full_name, role 
                FROM users 
                WHERE username = %s AND password = %s
                """,
                (username, password)
            )
            row = cursor.fetchone()

            if row:
                user_info = {
                    "id": row[0],
                    "username": row[1],
                    "full_name": row[2],
                    "role": row[3]
                }
                print(f"✅ Đăng nhập thành công: {username} - Role: {user_info['role']}")
                self.view.close()                  # Đóng login
                self.open_main_app(user_info)      # Mở Main Window
            else:
                self.view.show_error("Lỗi", "Tài khoản hoặc mật khẩu không đúng!")

        except Exception as e:
            self.view.show_error("Lỗi hệ thống", f"Lỗi khi truy vấn cơ sở dữ liệu:\n{str(e)}")
        finally:
            if conn:
                release_connection(conn)           # ← ĐÃ SỬA (dùng pool thay vì close)

    def open_main_app(self, user_info):
        """Mở giao diện chính sau khi login thành công"""
        self.main_controller = MainController(user_info=user_info)
        self.main_controller.run()

    def on_closing(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()