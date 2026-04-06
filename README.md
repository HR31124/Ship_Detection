# Hệ Thống Phát Hiện Và Phân Loại Tàu Thuyền  

Công cụ kiểm thử và đánh giá hiệu năng mô hình YOLO (Object Tracking) được xây dựng bằng Python và Tkinter. Ứng dụng hỗ trợ chạy các model đã train (định dạng `.pt`, `.onnx`, `.engine`) trên video, tự động xuất báo cáo hiệu năng (FPS, thời gian xử lý) và video kết quả.

## 🚀 Tính Năng Chính

* **Giao diện đồ họa (GUI):** Dễ dàng chọn thư mục Model, Video, Tracker và Output mà không cần sửa code.
* **Hỗ trợ Tracking đa dạng:** Tích hợp sẵn các thuật toán tracking (BoTSORT/ByteTrack/OCSORT/v.v.) để đếm đối tượng độc nhất (Unique ID).
* **Chọn Tracker động:** Combobox tự động quét thư mục `trackers/` và cho phép chọn file `.yaml` tracker.
* **2-Stage OCR (Tùy chọn):** Phát hiện và nhận dạng text trên tàu (sử dụng PaddleOCR).
* **Cấu hình linh hoạt:** Tùy chỉnh `Image Size`, `Skip Frame` (Stride), `Confidence Threshold`, và `Tracker` ngay trên giao diện.
* **Báo cáo tự động:**
    * Xuất video kết quả (`.mp4`) có vẽ khung tracking.
    * Xuất file CSV chứa dữ liệu chi tiết từng phát hiện (session-based).
    * Lưu ảnh tàu phát hiện vào `output/ship_images/`.
    * Xuất file TXT báo cáo tổng hợp.

## 📂 Cấu Trúc Dự Án

Dự án được tổ chức theo mô hình Modular để dễ dàng bảo trì và mở rộng:

```text
project_root/
│
├── src/
│   ├── controllers/        # Xử lý logic trung gian 
│   │   ├── __init__.py
│   │   ├── log_controller.py
│   │   └── main_controller.py
│   │
│   ├── engines/            # Xử lý AI / thuật toán
│   │   ├── __init__.py
│   │   ├── yolo_engine.py
│   │   ├── ocr_engine.py
│   │   ├── speed_estimator.py
│   │  
│   │
│   ├── models/             # Model AI (best.pt, yolo models)
│   │
│   ├── trackers/           # Tracker Config files (.yaml)
│   │   ├── botsort.yaml
│   │   ├── bytetrack.yaml
│   │
│   ├── views/              # Giao diện (UI)
│   │   ├── __init__.py
│   │   ├── log_view.py
│   │   └── main_view.py
│   │
│   ├── utils/              # Tiện ích (CSV Logger, export, helper)
│   │   ├── __init__.py
│   │   ├── csv_logger.py
│   │   ├── export_engine.py
│   │   └── report_utils.py
│   │
│   └── main.py             # Entry point
│
├── output/                 # Output từ ứng dụng
│   ├── shiplog.csv         # Log nhật ký tàu
│   └── ship_images/        # Ảnh tàu phát hiện
│
├── requirements.txt        # Thư viện Python
├── .gitignore
└── README.md
```

## Yêu Cầu Hệ Thống & Cài Đặt

### Yêu Cầu Tối Thiểu
- **Python:** 3.9+ (khuyến nghị 3.11+)
- **GPU:** NVIDIA RTX 1050 trở lên (có hỗ trợ CUDA)
- **CUDA:** 12.1+ (phù hợp với PyTorch 2.1.2+cu121)
- **cuDNN:** 8.x+
- **RAM:** 8GB+ (khuyến nghị 16GB)
- **Disk:** 10GB+ (cho models và output)

### Các Package Quan Trọng
```
PyTorch 2.1.2 (CUDA 12.1)
- torch 2.1.2+cu121
- torchvision 0.16.2+cu121
- torchaudio 2.1.2+cu121

Ultralytics YOLO
- ultralytics 8.4.8 (Object Detection & Tracking)

OCR & Computer Vision
- paddleocr 2.7.3 (Text OCR)
- paddlepaddle 2.6.2
- opencv-python 4.6.0.66

Data & Utilities
- pandas 3.0.0 (CSV handling)
- numpy 1.26.4
- scikit-learn 1.8.0
- scikit-image 0.26.0
```

### Các Bước Cài Đặt

#### Bước 1: Chuẩn Bị Môi Trường
Sử dụng Virtual Environment để tránh xung đột thư viện:
```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (Linux/Mac)
source venv/bin/activate
```

#### Bước 2: Nâng Cấp pip
```bash
python -m pip install --upgrade pip setuptools wheel
```

#### Bước 3: Cài Đặt Dependencies
Tùy theo cấu hình GPU của bạn, chọn phiên bản PyTorch phù hợp:

**Cho NVIDIA GPU (CUDA 12.1):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

**Cho CPU (không GPU):**
```bash
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

#### Bước 4: Kiểm Tra GPU (Tùy Chọn)
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## Hướng Dẫn Sử Dụng

### Khởi Chạy Ứng Dụng
Chạy file `src/main.py` từ terminal:
```bash
python src/main.py
```

### Thiết Lập Thông Số
1. **Chọn Model:** 
   - Nhấn "..." trong phần "Model" → Chọn file model (`.pt`, `.engine`, v.v.)

2. **Chọn Tracker:**
   - Combobox "Tracker" tự động quét thư mục `src/trackers/`
   - Chọn tracker muốn sử dụng (ví dụ: `bytetrack.yaml`, `botsort.yaml`)
   - Mặc định: `bytetrack.yaml`

3. **Chọn Video:**
   - Nhấn "..." trong phần "Video" → Chọn file video (`.mp4`, `.avi`, `.mov`, v.v.)

4. **Chọn Output:**
   - Nhấn "..." → Chọn thư mục lưu kết quả
   - Kết quả sẽ được lưu vào `output/shiplog.csv` và `output/ship_images/`

### Cấu Hình Advanced
- **Image Size:** Kích thước ảnh đầu vào cho model (Mặc định: 640)
- **Stride:** Số frame bỏ qua (Mặc định: 3 - xử lý 1/3 frame)
- **Confidence:** Ngưỡng tự tin để lọc kết quả (Slider: 0.0 - 1.0)
- **2-Stage OCR:** Bật/Tắt nhận dạng text tàu (cần chọn Text Model)

### Chạy Tracking
1. Nhấn nút **"▶ BẮT ĐẦU"**
2. Video sẽ phát với tracking thời gian thực
3. Nhấn **"⏹ DỪNG"** hoặc đóng cửa sổ để kết thúc

### Xem Kết Quả
Sau khi chạy xong, vào thư mục `output/`:
- **shiplog.csv:** Nhật ký phát hiện (track_id, class, OCR text, tốc độ, v.v.)
- **ship_images/:** Ảnh crop của tàu phát hiện
- **video.mp4:** Video tracking kết quả (nếu được xuất)

## Ghi Chú Quan Trọng

### CSV Logging
- Mỗi lần chạy được gán **Session ID** (tên video + timestamp)
- **Unique ID** được tạo từ `session_id_track_id` để tránh trùng lặp
- Dữ liệu được **tự động cập nhật** khi track_id đã tồn tại trong cùng session

### Tracker Selection
- File tracker phải có đuôi `.yaml` hoặc `.yml`
- Đặt file trong thư mục `src/trackers/`
- Ứng dụng sẽ tự động quét và hiển thị danh sách

## 🔧 Xử Lý Sự Cố (Troubleshooting)

### Lỗi: `CUDA out of memory`
**Giải pháp:**
- Giảm `Image Size` (ví dụ: 640 → 416)
- Tăng `Stride` để bỏ qua nhiều frame hơn (ví dụ: 3 → 5)
- Đóng các ứng dụng khác sử dụng VRAM

### Lỗi: `Could not find CUDA`
**Giải pháp:**
- Kiểm tra CUDA installation: `nvidia-smi`
- Cài đặt lại PyTorch với CUDA support:
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
  ```

### Lỗi: `Module 'paddle' not found`
**Giải pháp:**
```bash
pip install paddlepaddle paddleocr
```

### Video không hiển thị (OpenCV Error)
**Giải pháp:**
- Kiểm tra file video có bị corrupt không
- Cài đặt lại OpenCV (opencv-python-headless có thể gây vấn đề):
  ```bash
  pip uninstall opencv-python-headless
  pip install opencv-python
  ```

### Ứng dụng chạy chậm
**Giải pháp:**
- Kiểm tra GPU: `python -c "import torch; print(torch.cuda.is_available())"`
- Tăng Stride để bỏ qua frame
- Giảm Image Size
- Dùng model nhẹ hơn (ví dụ: yolov8n thay vì yolov8x)

### Track_ID bị reset
**Giải pháp:**
- Đây là hành vi bình thường - track_id được tạo mới với mỗi session
- Phân biệt giữa các session bằng cột `session_id` trong CSV
- Mỗi session có `unique_id` riêng: `session_id_track_id`

## 📊 Cơ Cấu File CSV

File `output/shiplog.csv` có các cột sau:

| Cột | Kiểu | Mô Tả |
|-----|------|-------|
| log_id | INT | ID tự tăng |
| unique_id | STR | Định danh duy nhất (session_id_track_id) |
| track_id | INT | ID phát hiện trong session hiện tại |
| session_id | STR | ID phiên (video_name + timestamp) |
| class_name | STR | Loại đối tượng (ví dụ: "speed_boat") |
| so_hieu_ocr | STR | Số hiệu tàu (từ OCR) |
| do_tin_cay_ocr | FLOAT | Độ tin cậy OCR (0-1) |
| toc_do_tb | FLOAT | Tốc độ trung bình (km/h) |
| gio_phat_hien | DATETIME | Thời gian phát hiện |
| hinh_anh_path | STR | Đường dẫn ảnh tàu |
| video_source | STR | Tên file video |

## 📦 Cấu Hình Khuyến Nghị

Dựa trên cấu hình của bạn **(RTX 1050, CUDA 12.1, Python 3.11)**:

```
✅ Python 3.11
✅ PyTorch 2.1.2 (CUDA 12.1)
✅ Ultralytics 8.4.8
✅ PaddleOCR 2.7.3
✅ Pandas 3.0.0
✅ OpenCV 4.6.0
```

**Lệnh cài đặt nhanh:**
```bash
# Tạo venv
python -m venv venv
venv\Scripts\activate

# Nâng cấp pip
python -m pip install --upgrade pip setuptools wheel

# Cài PyTorch CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Cài dependencies
pip install -r requirements.txt
```

## 📝 Ghi Chú & Hạn Chế

- **Training không hỗ trợ:** Tool này là dành cho testing model đã train, không hỗ trợ training.
- **Format video:** Hỗ trợ `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.flv`, `.webm`
- **GPU Memory:** RTX 1050 có 2GB VRAM - có thể cần giảm Image Size nếu gặp OOM
- **OCR:** Chỉ hoạt động nếu chọn Text Model và bật "Bật 2-Stage OCR"

## 🤝 Đóng Góp & Liên Hệ

Nếu gặp vấn đề hoặc có đề xuất, vui lòng:
1. Kiểm tra **Troubleshooting** trên
2. Tạo issue trên GitHub
3. Liên hệ qua email hoặc document dự án

---

**Cập nhật lần cuối:** April 7, 2026  
**Phiên bản:** 2.0  