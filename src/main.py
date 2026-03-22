# src/main.py
import sys
from pathlib import Path

# === FIX IMPORT SRC PACKAGE (quan trọng) ===
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.controllers.login_controller import LoginController

if __name__ == "__main__":
    login_controller = LoginController()
    login_controller.run()