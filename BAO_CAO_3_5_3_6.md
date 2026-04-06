# 3.5. XÂY DỰNG ỨNG DỤNG HỆ THỐNG

## 3.5.1. Kiến Trúc Tổng Thể (System Architecture)

Hệ thống Ship Detection được xây dựng theo **mô hình kiến trúc phân lớp (Layered Architecture)** với 4 tầng chính:

```
┌─────────────────────────────────────────────────────┐
│        TẦNG GIAO DIỆN (Presentation Layer)         │
│    - main_view.py: GUI Tkinter (Monitoring)       │
│    - log_view.py: Bảng dữ liệu Track log          │
└─────────────────────────────────────────────────────┘
                        ↓ Callback
┌─────────────────────────────────────────────────────┐
│      TẦNG ĐIỀU KHIỂN (Controller Layer)            │
│    - main_controller.py: Xử lý sự kiện & logic   │
│    - log_controller.py: Quản lý cơ sở dữ liệu     │
└─────────────────────────────────────────────────────┘
                        ↓ Command
┌─────────────────────────────────────────────────────┐
│        TẦNG CÔNG CỤ (Engine/Business Layer)       │
│    - yolo_engine.py: Phát hiện & Tracking         │
│    - ocr_engine.py: Nhận dạng ký hiệu tàu       │
│    - speed_estimator.py: Ước tính vận tốc         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│     TẦNG TIỆN ÍCH & DỮ LIỆU (Utility/Data)       │
│    - csv_logger.py: Ghi log CSV                  │
│    - export_engine.py: Xuất báo cáo               │
│    - report_utils.py: Tiện ích tạo báo cáo       │
└─────────────────────────────────────────────────────┘
```

---

## 3.5.2. Chi Tiết Từng Thành Phần

### A. TẦNG GIAO DIỆN (Views)

#### **main_view.py** - Giao Diện Giám Sát Chính
- **Chức năng:**
  - Hiển thị livestream xử lý từ video/camera
  - Chọn mô hình AI, video đầu vào, thư mục output
  - Điều chỉnh tham số: Image Size, Skip Frame, Confidence Threshold
  - Chọn thuật toán tracking (BoTSORT, ByteTrack, OCSORT)
  - Hiển thị chi tiết tàu khi click vào bounding box

- **Các Widgets Chính:**
  ```python
  - Model selector: Combobox chọn model YOLO (.pt, .engine)
  - Video selector: Lựa chọn file video/livestream
  - Output folder: Thư mục lưu kết quả
  - Tracker dropdown: Chọn file .yaml từ thư mục trackers/
  - Canvas: Hiển thị frame video đang xử lý
  - Parameters panel: Image Size, Skip Frame, Confidence
  - OCR mode toggle: Bật/tắt nhận dạng ký hiệu
  ```

#### **log_view.py** - Bảng Nhật Ký Phát Hiện
- **Chức năng:**
  - Hiển thị danh sách tất cả các tàu phát hiện từ phiên làm việc hiện tại
  - Bảng dữ liệu: Track ID, Class, OCR, Speed, Timestamp
  - Xem cropped image của tàu
  - Chỉnh sửa thông tin OCR thủ công
  - Xóa bản ghi không chính xác

- **Dữ Liệu Hiển Thị:**
  ```
  Track ID | Class | OCR | Speed (km/h) | Confidence | Last Update
  ────────────────────────────────────────────────────────────────
  1        | Fishing  | ABC123 | 15.5 | 0.92 | 14:23:45
  2        | Passenger| XYZ456 | 22.1 | 0.88 | 14:23:46
  ```

---

### B. TẦNG ĐIỀU KHIỂN (Controllers)

#### **main_controller.py** - Bộ Điều Khiển Chính
Kế thừa từ lớp `Tkinter.Tk`, quản lý toàn bộ luồng ứng dụng:

```python
class MainController:
    └── __init__()
        ├── MainView(callbacks)          # Khởi tạo GUI
        └── LogController()              # Khởi tạo bộ điều khiển nhật ký
    
    ├── choose_model()                   # Mở dialog chọn model
    ├── choose_video()                   # Chọn file video
    ├── choose_output_folder()           # Lựa chọn thư mục output
    │
    ├── start_process()                  # Bắt đầu xử lý
    │   └── YoloTester(params)          # Khởi tạo engine
    │       └── threading.Thread()      # Chạy file video trong thread riêng
    │
    ├── stop_process()                   # Dừng xử lý
    ├── on_canvas_click(event)          # Xử lý click trên frame video
    └── on_auto_ocr_complete()          # Callback khi OCR hoàn thành
```

**Các Callback Chính:**
1. `choose_model()` - Chọn mô hình phát hiện tàu
2. `choose_video()` - Chọn video đầu vào
3. `start_process()` - Bắt đầu xử lý (tạo engine + thread)
4. `stop_process()` - Dừng xử lý hiện tại
5. `on_canvas_click()` - Nhấp chuột để xem chi tiết tàu
6. `refresh_current_page()` - Làm mới dữ liệu F5

#### **log_controller.py** - Bộ Điều Khiển Nhật Ký
- **Chức năng chính:**
  - Đọc/ghi file CSV chứa log phát hiện
  - Quản lý cơ sở dữ liệu nhật ký phiên làm việc
  - Xử lý OCR thủ công (manual re-OCR)
  - Lọc & tìm kiếm bản ghi

```python
class LogController:
    ├── __init__(root, view)
    ├── refresh_database()              # Tải lại dữ liệu từ CSV
    ├── on_tree_select(event)           # Xử lý chọn dòng trong bảng
    ├── manual_ocr()                    # OCR lại bằng tay
    ├── set_output_folder(path)         # Cập nhật thư mục output
    └── on_auto_ocr_complete()          # Cập nhật bản ghi mới từ engine
```

---

### C. TẦNG CÔNG CỤ & XỬ LÝ (Engines)

#### **yolo_engine.py** - Công Cụ Phát Hiện & Tracking

**Kiến trúc xử lý video:**

```
Input Video (mp4/avi)
        ↓
[Frame Reader] (stride = Skip Frame)
        ↓
[YOLO Model] → Phát hiện tàu (bbox + class + confidence)
        ↓
[Tracker (ByteTrack/BoTSORT)] → Gán Track ID (nhận dạng đối tượng giữa frames)
        ↓
[Speed Estimator] → Tính vận tốc (km/h) dựa trên pixel displacement
        ↓
[OCR Queue] → Gửi crop image tới OCR worker thread (2-stage)
        ↓
[Output Multi-threading]:
  ├── Ghi frame có bbox vào video output (.mp4)
  ├── Lưu ảnh tàu vào ship_images/
  └── Ghi log CSV (Track ID, Class, OCR, Speed...)
```

**Các Tham Số Cấu Hình:**
```python
YoloTester(
    model_path="best.pt",          # YOLO model (detection)
    input_source="video.mp4",      # Video đầu vào
    output_folder="./output",      # Thư mục output
    conf=0.5,                      # Confidence threshold
    imgsz=640,                     # Input image size (chia lẻ)
    stride=1,                      # Skip frame (1=xử lý mỗi frame, 5=mỗi 5 frames)
    use_ocr=True,                  # Bật 2-stage OCR
    text_model_path="text.pt",     # Text detection model (OCR stage 1)
    tracker="bytetrack.yaml"       # File config tracker
)
```

**2-Stage OCR Architecture:**
```
Crop Image (tàu phát hiện)
        ↓
[Stage 1: Text Detection]
  - Dùng text_model.pt (YOLO) detect vùng chứa chữ/số
        ↓
[Stage 2: Text Recognition]
  - PaddleOCR nhận dạng chữ từ vùng detected
        ↓
Result: "ABC123" (ký hiệu/biển số tàu)
```

#### **ocr_engine.py** - Công Cụ OCR

```python
class ShipOCR:
    ├── __init__()                      # Initialize PaddleOCR
    ├── recognize_text(img)             # Nhận dạng text từ image
    └── detect_text_region(img)         # Detect vùng chứa text
```

- **Sử dụng:** PaddleOCR (hỗ trợ tiếng Việt + chữ số, ký hiệu)
- **Luồng:** Nhận image crop → Detect text region → OCR → Trả về string

#### **speed_estimator.py** - Công Cụ Ước Tính Vận Tốc

```python
class SpeedEstimator:
    ├── __init__(calibration_params)
    ├── estimate_speed(bbox_prev, bbox_cur, fps)  # Tính vận tốc
    └── pixel_to_kmh(pixel_distance)              # Chuyển pixel → km/h
```

**Công Thức:**
```
vận_tốc (km/h) = (pixel_distance × fps × calibration_factor) / fps
                = pixel_distance × calibration_factor
```
- Dựa trên displacement của bounding box giữa 2 frames
- Calibration factor được thiết lập dựa trên độ phân giải & khoảng cách camera

---

### D. TẦNG TIỆN ÍCH & DỮ LIỆU (Utils)

#### **csv_logger.py** - Ghi Log CSV

```python
class CSVLogger:
    ├── __init__(output_folder, session_id)
    ├── log_detection(track_id, class_name, bbox, confidence, ocr, speed)
    └── get_logger()                    # Trả về logger instance
```

**Cấu Trúc CSV Output:**
```csv
timestamp,track_id,class_name,bbox_x1,bbox_y1,bbox_x2,bbox_y2,confidence,ocr,speed_kmh,image_path
2024-01-15 14:23:45,1,fishing_boat,100,150,250,300,0.92,ABC123,15.2,"output/ship_images/ship_1_001.jpg"
2024-01-15 14:23:46,2,passenger_ship,500,200,700,400,0.88,XYZ456,22.5,"output/ship_images/ship_2_001.jpg"
```

#### **export_engine.py** - Xuất Báo Cáo

```python
class ExportEngine:
    ├── export_video(frames, fps)       # Xuất video .mp4 với bbox
    ├── export_images(ship_crops)       # Lưu ảnh tàu
    └── generate_report(stats)          # Tạo file báo cáo TXT
```

#### **report_utils.py** - Tiện Ích Báo Cáo

```python
def save_test_report(output_folder, stats):
    """
    Lưu báo cáo tổng hợp:
    - Số tàu phát hiện tổng cộng
    - FPS trung bình
    - Thống kê theo loại tàu
    - Thời gian xử lý
    """
```

**Ví dụ báo cáo:**
```
═══════════════════════════════════════════
  SHIP DETECTION TEST REPORT
═══════════════════════════════════════════

Session ID: video.mp4_1705330425
Processing Time: 45.23 seconds
Total Frames: 1350
Average FPS: 29.8

DETECTION STATISTICS:
─────────────────────
Total Ships Detected: 28
- Fishing Boats: 12
- Passenger Ships: 10
- Speed Boats: 6

Average Confidence: 0.91
Unique Tracked Objects: 28
═══════════════════════════════════════════
```

---

## 3.5.3. Luồng Xử Lý Chi Tiết (Processing Pipeline)

### Phiên Làm Việc (Session) - Từ Khởi Động Đến Kết Thúc:

```
┌─── START ──────────────────────────────────────────┐
│                                                    │
│  1. MainController.__init__()                     │
│     ├── MainView (GUI Tkinter)                   │
│     └── LogController (CSV manager)              │
│                                                   │
│  2. User Interaction (Click buttons):            │
│     ├── Choose Model (browse dialog)             │
│     ├── Choose Video (browse dialog)             │
│     ├── Set Parameters (Image Size, Skip Frame)  │
│     ├── Choose Tracker (dropdown)                │
│     └── Click "Start Process"                    │
│                                                   │
│  3. start_process() - Khởi Động Engine:         │
│     ├── YoloTester.__init__()                   │
│     │   ├── Load YOLO Model                     │
│     │   ├── Initialize OCR Engine               │
│     │   ├── Start OCR Worker Thread             │
│     │   └── Initialize Tracker Config           │
│     │                                            │
│     └── threading.Thread(engine.run())          │
│         (Chạy xử lý video trong thread riêng)   │
│                                                   │
│  4. engine.run() - Vòng Lặp Xử Lý Video:       │
│     └── While (video.is_open()) and not stop:  │
│         ├── Read Frame (stride skip)            │
│         ├── YOLO Inference (detections)         │
│         ├── Tracker.update() (track IDs)        │
│         ├── Speed Estimation (km/h)             │
│         ├── Crop + Queue to OCR                 │
│         ├── Draw Boxes on Frame                 │
│         ├── Update GUI (callbacks)              │
│         └── Write Frame to Output Video         │
│             └── CSV Log                         │
│                                                   │
│  5. OCR Worker Thread - Parallel Processing:   │
│     └── While queue.not_empty():                │
│         ├── Pop (track_id, crop_img)            │
│         ├── Stage 1: Text Detection (YOLO)     │
│         ├── Stage 2: Text Recognition (OCR)    │
│         └── Update CSV → LogView                │
│                                                   │
│  6. User Clicks "Stop Process":                │
│     └── engine.stop_event = True                │
│         └── Thread terminates                    │
│             └── Save Final Report               │
│                                                   │
└─── END ────────────────────────────────────────┘
```

---

## 3.5.4. Công Nghệ & Thư Viện Sử Dụng

| Thành Phần | Thư Viện | Phiên Bản | Chức Năng |
|-----------|---------|---------|----------|
| **Deep Learning** | PyTorch + CUDA | 2.1.2 + 12.1 | Inference GPU |
| **Object Detection** | Ultralytics YOLO | 8.4.8 | Phát hiện tàu |
| **Object Tracking** | ByteTrack/BoTSORT | Built-in | Tracking tàu |
| **OCR** | PaddleOCR | 2.7.3 | Nhận dạng chữ |
| **Image Processing** | OpenCV | 4.6.0 | Frame processing |
| **GUI** | Tkinter | Built-in | Giao diện |
| **Data Handling** | Pandas | 3.0.0 | CSV logging |
| **Async Processing** | Threading | Built-in | OCR parallel |

---

## 3.5.5. Xử Lý Lỗi & An Toàn

- **Exception Handling:** Try-catch cho load model, OCR, video reading
- **Resource Management:** 
  - Đóng file video sau khi xử lý xong
  - Giải phóng GPU memory sau inference
- **Thread Safety:** Queue để giao tiếp giữa main thread và OCR worker
- **Validation:**
  - Kiểm tra file tồn tại trước khi load
  - Kiểm tra độ phân giải video hợp lệ
  - Validate parameters (conf, imgsz, stride)

---

---

# 3.6. TRIỂN KHAI HỆ THỐNG

## 3.6.1. Quy Trình Triển Khai (Deployment Process)

### Phase 1: Chuẩn Bị Môi Trường

#### **Yêu Cầu Hệ Thống (System Requirements)**

| Yêu Cầu | Tối Thiểu | Khuyến Nghị |
|--------|----------|-----------|
| **Python Version** | 3.9 | 3.11.x |
| **GPU** | RTX 1050 (2GB) | RTX 3070+ (8GB+) |
| **CUDA Version** | 11.8 | 12.1+ |
| **cuDNN** | 8.x | 8.x |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 10 GB | 20 GB |
| **OS** | Windows 10+ / Linux | Windows 11 / Ubuntu 22.04 |

#### **Chuẩn Bị Trước Triển Khai**

```bash
# 1. Tải và cài Python 3.11
# https://www.python.org/downloads/

# 2. Cài NVIDIA CUDA 12.1
# https://developer.nvidia.com/cuda-12-1-0-download-target-os-x86_64

# 3. Cài cuDNN (NVIDIA account required)
# https://developer.nvidia.com/cudnn

# 4. Thêm CUDA bin vào PATH (Windows)
# C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin
```

---

### Phase 2: Cài Đặt Dự Án

#### **Step 1: Clone / Copy Dự Án**

```bash
# Option A: Clone từ Git
git clone <repository_url>
cd Ship_Detection_ThucTap

# Option B: Copy folder dự án
# D:\ThucTapDoAn\Ship_Detection_ThucTap - Copy
```

#### **Step 2: Tạo Virtual Environment**

```powershell
# Windows - PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows - CMD
python -m venv venv
venv\Scripts\activate.bat

# Linux / Mac
python3 -m venv venv
source venv/bin/activate
```

#### **Step 3: Cài Đặt Dependencies**

```bash
# Nâng cấp pip
pip install --upgrade pip setuptools wheel

# Cài PyTorch với CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Cài tất cả dependencies
pip install -r requirements.txt
```

**Các gói chính:**
- `ultralytics==8.4.8` - YOLO detection
- `paddleocr==2.7.3` - Text OCR
- `opencv-python==4.6.0.66` - Image processing
- `pandas==3.0.0` - CSV handling
- `numpy==1.26.4` - Numerical computing

#### **Step 4: Xác Minh Cài Đặt**

```bash
# Kiểm tra PyTorch + GPU
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

# Kiểm tra YOLO
python -c "from ultralytics import YOLO; print('YOLO imported successfully')"

# Kiểm tra OCR
python -c "from paddleocr import PaddleOCR; print('PaddleOCR imported successfully')"
```

---

### Phase 3: Chuẩn Bị Dữ Liệu

#### **Cấu Trúc Thư Mục Bắt Buộc**

```
Project Root/
├── models/                              # Thư mục model YOLO
│   ├── best.pt                         # Model detection tàu (bắt buộc)
│   ├── best (8).pt                     # Model thay thế
│   └── yolov12x_fish-speed-pass.pt     # Model cải tiến
│
├── videos/                              # Thư mục video input
│   ├── video1.mp4
│   ├── video2.avi
│   └── ... (các file video khác)
│
├── src/
│   ├── trackers/                        # Config file tracker
│   │   ├── botsort.yml                 # Bắt buộc
│   │   └── bytetrack.yml               # Bắt buộc
│   │
│   └── ... (các file code)
│
└── output/                              # Output sẽ được tạo tự động
    ├── shiplog.csv
    └── ship_images/
```

#### **Tải Model & Dữ Liệu**

```bash
# Tạo thư mục models nếu chưa tồn tại
mkdir models
mkdir videos

# Tải model YOLO từ Hugging Face / Google Drive
# Lưu vào thư mục models/

# Chuẩn bị video test
# Lưu các file video (.mp4, .avi) vào thư mục videos/

# Mở file config tracker (trackers/bytetrack.yml)
# Đảm bảo format YAML đúng
```

---

### Phase 4: Chạy Ứng Dụng

#### **Khởi Động Ứng Dụng**

```bash
# Đảm bảo virtual environment đang active
# .\venv\Scripts\Activate.ps1 (Windows)
# source venv/bin/activate (Linux/Mac)

# Chạy ứng dụng
python src/main.py
```

#### **Giao Diện Khởi Động**

```
┌────────────────────────────────────────────────────┐
│  AI Ship Detection System                          │
├────────────────────────────────────────────────────┤
│  [🏠 Hệ thống giám sát] [📊 Nhật ký phát hiện]    │
├────────────────────────────────────────────────────┤
│                                                    │
│  🎥 Chọn Mô Hình:      [Browse...] best.pt      │
│  📹 Chọn Video:        [Browse...] video.mp4    │
│  📂 Thư Mục Output:    [Browse...] ./output     │
│                                                   │
│  ⚙️  Tham Số Xử Lý:                               │
│    Image Size: [640]   Skip Frame: [1]           │
│    Confidence: [0.5━━━━] OCR: [✓ Bật]           │
│    Tracker: [bytetrack.yml ▼]                    │
│                                                   │
│  [▶ Bắt Đầu]  [⏹ Dừng]  [F5 Làm Mới]           │
│                                                   │
│  [Live Feed - Frame 0/0 - FPS: 0]                │
│  ┌──────────────────────────────────────────┐    │
│  │                                          │    │
│  │         (Video display area)             │    │
│  │                                          │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
└────────────────────────────────────────────────────┘
```

#### **Bước Sử Dụng (Usage Steps)**

```
1. Click "Browse" để chọn Model YOLO (best.pt)
   → Chọn từ thư mục models/

2. Click "Browse" để chọn Video Input
   → Chọn từ thư mục videos/

3. Click "Browse" để chọn Output Directory
   → Tạo thư mục mới hoặc chọn thư mục hiện tại

4. (Tùy chọn) Chọn Model OCR nếu bật OCR
   → Chọn model text detection (.pt)

5. Điều chỉnh Tham Số:
   - Image Size: 640 (default) hoặc 1280 (cao hơn)
   - Skip Frame: 1 (xử lý mỗi frame) hoặc 5 (tăng speed)
   - Confidence: 0.5 (default) hoặc 0.7 (chặt hơn)
   - Tracker: Chọn ByteTrack (nhanh) hoặc BoTSORT (chính xác)

6. Click "▶ Bắt Đầu"
   → Xử lý video bắt đầu
   → Xem realtime feed & thống kê FPS

7. Chuyển tab "📊 Nhật ký phát hiện" để xem log
   → Bảng hiển thị các tàu phát hiện
   → Click row để xem chi tiết ảnh + OCR

8. Khi hoàn thành, Click "⏹ Dừng"
   → Xuất báo cáo tự động
   → Video output được lưu: output/result_*.mp4
```

---

## 3.6.2. Cấu Hình Chi Tiết (Configuration)

### **A. Tracker Configuration (trackers/*.yml)**

#### **bytetrack.yml - Nhanh & Phù Hợp Video Tàu**

```yaml
# ByteTrack Config
# Ref: https://github.com/ifzhang/ByteTrack

tracker_type: "bytetrack"
reid_weights: "path/to/osnet_x0_25_msmt17.pt"  # Optional
max_age: 30          # Frames để xóa track không detect
min_hits: 3          # Min detections để tạo track (mới)
iou_threshold: 0.2   # IOU threshold untuk matching
high_score_threshold: 0.6  # High confidence detections
low_score_threshold: 0.1   # Low confidence matching
```

#### **botsort.yml - Chính Xác Hơn**

```yaml
# BoTSORT Config  
# Ref: https://github.com/NirAharon/BoTSORT

tracker_type: "botsort"
track_high_thresh: 0.6              # High confidence threshold
track_low_thresh: 0.1               # Low confidence threshold
new_track_thresh: 0.7               # New track threshold
track_buffer: 30                    # Frames để giữ track
match_thresh: 0.8                   # Matching threshold
```

### **B. Tham Số YOLO (yolo_engine.py)**

```python
# Cái đặt mặc định
self.conf = 0.5      # Confidence threshold (0.0-1.0)
self.imgsz = 640     # Input size (320, 416, 512, 640, 1280)
self.stride = 1      # Skip frame (1=all, 5=every 5th)
self.device = "0"    # GPU device ID (0=first GPU)
```

### **C. Biến Môi Trường (Environment Variables)**

```bash
# Windows - Thiết lập trong .env hoặc System Properties
set CUDA_VISIBLE_DEVICES=0          # GPU device
set KMP_DUPLICATE_LIB_OK=TRUE       # Fix PyTorch DLL warning

# Linux / Mac
export CUDA_VISIBLE_DEVICES=0
export KMP_DUPLICATE_LIB_OK=TRUE
```

---

## 3.6.3. Quản Lý Output

### **Cấu Trúc Output (Tự Động Tạo)**

```
output/
├── shiplog.csv
│   └── CSV Log của session hiện tại
│       - Mỗi dòng = 1 lần detect
│       - Columns: timestamp, track_id, class, bbox, conf, ocr, speed
│
├── ship_images/
│   ├── ship_1_001.jpg       # Crop tàu ID=1, frame 1
│   ├── ship_1_002.jpg       # Crop tàu ID=1, frame 2
│   ├── ship_2_001.jpg       # Crop tàu ID=2, frame 1
│   └── ... (100+ ảnh)
│
├── result_video.mp4         # Video output với bbox
│   └── Có vẽ bounding box, track ID, OCR, speed
│
└── report_*.txt             # Báo cáo tổng hợp
    └── Tổng số tàu, FPS, thống kê
```

### **Định Dạng CSV Output**

```csv
timestamp,track_id,class_name,bbox_x1,bbox_y1,bbox_x2,bbox_y2,confidence,ocr,speed_kmh,image_path
2024-01-15 14:23:45.123,1,fishing_boat,100,150,250,300,0.92,ABC-123,15.2,output/ship_images/ship_1_001.jpg
2024-01-15 14:23:46.152,1,fishing_boat,105,152,255,302,0.91,ABC-123,15.5,output/ship_images/ship_1_002.jpg
2024-01-15 14:23:46.152,2,passenger_ship,500,200,700,400,0.88,XYZ-456,22.5,output/ship_images/ship_2_001.jpg
```

---

## 3.6.4. Troubleshooting & Maintenance

### **Vấn Đề Thường Gặp & Giải Pháp**

| Vấn Đề | Nguyên Nhân | Giải Pháp |
|-------|-----------|----------|
| **CUDA Not Available** | GPU driver outdated | Cập nhật NVIDIA GPU driver |
| **Model Load Failed** | File model không tồn tại | Kiểm tra đường dẫn model |
| **Out of Memory (OOM)** | Batch size quá lớn | Giảm `imgsz` từ 640 → 416 |
| **Slow FPS** | Skip frame = 1 | Tăng stride lên 3-5 |
| **OCR Not Working** | PaddleOCR chưa download | `paddleocr` tự download models |
| **Tracker Errors** | Config YAML sai format | Kiểm tra indentation YAML |

### **Memory Management**

```python
# Giải phóng GPU sau khi xử lý
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    torch.cuda.synchronize()

# Monitor GPU usage
# Windows: nvidia-smi
# Command: watch -n 1 nvidia-smi (Linux)
```

### **Logging & Debugging**

```bash
# Chạy với verbose output
python src/main.py 2>&1 | tee debug.log

# Check các files được tạo
dir output/
dir output/ship_images/

# Verify CSV
python -c "import pandas as pd; df=pd.read_csv('output/shiplog.csv'); print(df.head())"
```

---

## 3.6.5. Backup & Version Control

### **Git Setup (Version Control)**

```bash
# Khởi tạo repo
git init
git remote add origin <repo_url>

# Add files (ignore venv, models, output)
git add .
git commit -m "Initial Ship Detection System"

# .gitignore (đã có sẵn)
venv/
__pycache__/
*.pyc
models/*.pt
output/
*.log
```

### **Backup Chiến Lược**

```
Backup Schedule:
├── Hàng ngày: CSV logs (shiplog.csv)
├── Hàng tuần: Model weights (models/)
├── Hàng tháng: Toàn bộ codebase
└── After deployment: Tag version (git tag)
```

---

## 3.6.6. Monitoring & Performance

### **Key Metrics to Track**

```
┌──────────────────────────────────────┐
│     PERFORMANCE METRICS              │
├──────────────────────────────────────┤
│ FPS (Frames Per Second)              │
│ └─ Target: > 20 FPS                 │
│                                      │
│ GPU Memory Usage                     │
│ └─ Target: < 6 GB (RTX 3070)        │
│                                      │
│ Detection Confidence                 │
│ └─ Avg: > 0.85                      │
│                                      │
│ Processing Latency                   │
│ └─ Per frame: < 50ms                │
│                                      │
│ Tracking Accuracy                    │
│ └─ Unique IDs maintained             │
└──────────────────────────────────────┘
```

### **Performance Optimization Tips**

1. **Giảm Input Resolution:**
   ```python
   imgsz = 416  # Thay vì 640 → -30% time
   ```

2. **Skip Frames:**
   ```python
   stride = 5   # Xử lý mỗi 5 frame → +400% speed
   ```

3. **Batch Processing (nếu có)**
   ```python
   batch_size = 4  # Process 4 frames cùng lúc
   ```

4. **Disable OCR nếu không cần:**
   ```python
   use_ocr = False  # OCR là bottleneck chính
   ```

---

## 3.6.7. Deployment Checklist

```
PRE-DEPLOYMENT CHECKLIST
═══════════════════════════════════════════════════

☐ Cài Python 3.11 + CUDA 12.1 + cuDNN 8.x
☐ Tạo Virtual Environment (venv)
☐ Cài đặt requirements.txt
☐ Verify PyTorch + GPU (torch.cuda.is_available())
☐ Verify YOLO import
☐ Verify OCR import (PaddleOCR)

☐ Chuẩn bị Model Files:
  ☐ best.pt (Detection model) vào models/
  ☐ Text detection model (nếu dùng OCR) 
  
☐ Chuẩn bị Video Input:
  ☐ Copy video files vào videos/
  ☐ Kiểm tra format (mp4/avi)
  
☐ Kiểm tra Config:
  ☐ trackers/bytetrack.yml hoặc botsort.yml
  ☐ Verify file paths
  
☐ Test Run:
  ☐ Chạy python src/main.py
  ☐ GUI hiển thị đúng
  ☐ Chọn model → Load thành công
  ☐ Chọn video → Load thành công
  ☐ Bắt đầu xử lý → FPS > 0
  ☐ Output được tạo (CSV, video, ảnh)

☐ Verify Output:
  ☐ shiplog.csv chứa dữ liệu
  ☐ ship_images/ chứa ảnh crop
  ☐ result_video.mp4 có bbox
  ☐ report_*.txt generated

═══════════════════════════════════════════════════
```

---

## 3.6.8. Post-Deployment (Sau Triển Khai)

### **Monitoring & Maintenance**

```bash
# Daily Checks
1. Verify GPU driver (nvidia-smi)
2. Check disk space (output/ size)
3. Review CSV logs for anomalies

# Weekly Maintenance
1. Clean up old CSV logs
2. Archive ship_images/
3. Update requirements.txt nếu cần

# Monthly Review
1. Performance analysis (FPS trend)
2. Model accuracy evaluation
3. Update YOLO model nếu có version mới
```

### **Update & Upgrade**

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update YOLO
pip install --upgrade ultralytics

# Update PaddleOCR
pip install --upgrade paddleocr

# Check versions
pip list | grep -E "torch|ultralytics|paddleocr"
```

---

## **CONCLUSION - TÓM TẮT**

Hệ thống Ship Detection được triển khai dựa trên kiến trúc **Modular Layered Architecture** với 4 tầng rõ ràng, cho phép:

✅ **Dễ bảo trì** - Mỗi module độc lập  
✅ **Dễ mở rộng** - Thêm tracker, engine mới  
✅ **Hiệu năng cao** - Multi-threading OCR  
✅ **User-friendly** - GUI Tkinter intuitif  
✅ **Flexible** - Tùy chỉnh parameter dễ dàng  

Triển khai yêu cầu chuẩn bị:
1. **Môi trường** (Python + CUDA + GPU driver)
2. **Dependencies** (PyTorch, YOLO, OCR, OpenCV)
3. **Dữ liệu** (Model weights + Video input)
4. **Configuration** (Tracker config + Parameters)

Sau khi triển khai, hệ thống hoạt động 24/7 với:
- Xử lý video real-time (FPS > 20)
- Tracking tàu chính xác (Unique IDs)
- OCR 2-stage (High accuracy)
- Output đa dạng (CSV, Video, Images, Report)

