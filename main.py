import tkinter as tk
import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.login import LoginWindow
from gui.main_window import App

def start_main_app():
    """Hàm này sẽ chạy sau khi người dùng đăng nhập thành công"""

    main_root = tk.Tk()
    app = App(main_root)

    main_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    main_root.mainloop()

if __name__ == "__main__":

    login_root = tk.Tk()

    login_app = LoginWindow(login_root, success_callback=start_main_app)
    
    login_root.mainloop()