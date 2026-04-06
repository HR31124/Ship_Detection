# src/main.py
import os
import sys
from pathlib import Path

def fix_torch_dll():
    project_root = Path(__file__).resolve().parent.parent
    torch_lib_path = project_root / "venv" / "Lib" / "site-packages" / "torch" / "lib"
    
    if torch_lib_path.exists():
        os.add_dll_directory(str(torch_lib_path))
    
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

fix_torch_dll()

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.controllers.main_controller import MainController


if __name__ == "__main__":
    try:
        print("Đang khởi động hệ thống Ship Detection...")
        main_controller = MainController()
        main_controller.run()
    except Exception as e:
        print(f"Có lỗi xảy ra khi khởi động: {e}")
        import traceback
        traceback.print_exc()
        input("Nhấn Enter để thoát...")