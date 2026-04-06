"""
CSV Logger - Thay thế Database cho việc lưu trữ nhật ký phát hiện tàu
Sử dụng pandas và lock để đảm bảo thread-safe khi ghi file
"""

import os
import csv
import pandas as pd
from datetime import datetime
from threading import Lock
from pathlib import Path
from typing import List, Dict, Optional


class CSVLogger:
    """Logger để quản lý nhật ký phát hiện tàu qua CSV file"""
    
    # Cột của CSV file
    CSV_COLUMNS = [
        'log_id',           # Auto-increment ID
        'unique_id',        # Unique ID kết hợp session_id + track_id (session_id_trackId)
        'track_id',         # Tracking ID từ YOLO
        'session_id',       # Session ID (tên video + timestamp)
        'class_name',       # Loại tàu (e.g., 'fishing_boat', 'speed_boat', 'passenger')
        'so_hieu_ocr',      # Số hiệu tàu (từ OCR)
        'do_tin_cay_ocr',   # Confidence score của OCR (0-1)
        'toc_do_tb',        # Tốc độ trung bình (km/h)
        'gio_phat_hien',    # Giờ phát hiện (timestamp)
        'hinh_anh_path',    # Đường dẫn ảnh tàu (relative path)
        'video_source',     # Tên file video hoặc nguồn camera
    ]
    
    def __init__(self, log_dir: str = None):
        """
        Khởi tạo CSV Logger
        
        Args:
            log_dir: Thư mục chứa file shiplog.csv (mặc định: output/)
        """
        if log_dir is None:
            log_dir = "output"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.csv_path = self.log_dir / "shiplog.csv"
        self.lock = Lock()
        
        # Khởi tạo file CSV nếu chưa tồn tại
        self._initialize_csv()
        
        # Counter cho log_id
        self.log_counter = self._get_next_log_id()
    
    def _initialize_csv(self):
        """Tạo file CSV với header nếu chưa tồn tại, hoặc migrate nếu cần"""
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_COLUMNS)
            print(f">> CSV Logger: Tạo file {self.csv_path}")
        else:
            # Kiểm tra nếu file cũ không có cột unique_id, thêm vào
            try:
                df = pd.read_csv(self.csv_path)
                if 'unique_id' not in df.columns:
                    print(">> CSV Logger: Phát hiện file cũ - migrating để thêm cột unique_id...")
                    # Tạo unique_id từ session_id + track_id
                    df['unique_id'] = df['session_id'] + '_' + df['track_id'].astype(str)
                    # Sắp xếp lại cột theo đúng thứ tự
                    df = df[self.CSV_COLUMNS]
                    df.to_csv(self.csv_path, index=False, encoding='utf-8')
                    print(">> CSV Logger: Migration thành công - thêm cột unique_id")
                else:
                    print(f">> CSV Logger: Sử dụng file {self.csv_path}")
            except Exception as e:
                print(f">> CSV Logger Warning: {e}, sẽ tiếp tục...")
    
    def _get_next_log_id(self) -> int:
        """Lấy log_id tiếp theo"""
        try:
            df = pd.read_csv(self.csv_path)
            if df.empty:
                return 1
            return int(df['log_id'].max()) + 1 if 'log_id' in df.columns else 1
        except Exception as e:
            print(f">> Warning: Lỗi đọc log_id từ CSV: {e}")
            return 1
    
    def append_log(self, track_id: int, session_id: str, class_name: str, 
                   video_source: str, so_hieu_ocr: str = "N/A", 
                   do_tin_cay_ocr: float = 0.0, toc_do_tb: float = 0.0,
                   hinh_anh_path: str = "", gio_phat_hien: str = None) -> int:
        """
        Thêm một dòng mới vào CSV file
        Đảm bảo (session_id, track_id) là duy nhất - nếu đã tồn tại thì update thay vì insert
        
        Args:
            track_id: Tracking ID
            session_id: Session ID
            class_name: Loại tàu
            video_source: Tên video/camera
            so_hieu_ocr: Số hiệu tàu
            do_tin_cay_ocr: Confidence OCR
            toc_do_tb: Tốc độ trung bình
            hinh_anh_path: Đường dẫn ảnh
            gio_phat_hien: Giờ phát hiện (mặc định: hiện tại)
        
        Returns:
            log_id của entry vừa tạo hoặc cập nhật
        """
        if gio_phat_hien is None:
            gio_phat_hien = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tạo unique_id từ session_id + track_id
        unique_id = f"{session_id}_{track_id}"
        
        with self.lock:
            try:
                # Kiểm tra xem (session_id, track_id) đã tồn tại chưa
                df = pd.read_csv(self.csv_path)
                existing_mask = (df['session_id'] == session_id) & (df['track_id'] == track_id)
                
                if not existing_mask.empty and existing_mask.any():
                    # Nếu đã tồn tại, cập nhật dòng cuối cùng
                    existing_rows = df[existing_mask]
                    last_idx = existing_rows.index[-1]
                    
                    # Cập nhật nếu giá trị mới có ý nghĩa
                    if hinh_anh_path:
                        df.at[last_idx, 'hinh_anh_path'] = hinh_anh_path
                    
                    df.to_csv(self.csv_path, index=False, encoding='utf-8')
                    log_id = int(df.at[last_idx, 'log_id'])
                    print(f">> CSV: Cập nhật entry [unique_id={unique_id}, class={class_name}]")
                    return log_id
                
                # Nếu chưa tồn tại, thêm dòng mới
                log_id = self.log_counter
                self.log_counter += 1
                
                row = [
                    log_id,
                    unique_id,
                    track_id,
                    session_id,
                    class_name,
                    so_hieu_ocr,
                    do_tin_cay_ocr,
                    toc_do_tb,
                    gio_phat_hien,
                    hinh_anh_path,
                    video_source,
                ]
                
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
                
                print(f">> CSV: Thêm log [unique_id={unique_id}, class={class_name}]")
                return log_id
                
            except Exception as e:
                print(f">> CSV Error: Lỗi append_log: {e}")
                return -1
    
    def update_log(self, track_id: int, session_id: str, 
                   so_hieu_ocr: str = None, do_tin_cay_ocr: float = None, 
                   toc_do_tb: float = None, hinh_anh_path: str = None) -> bool:
        """
        Cập nhật dòng log cuối cùng của track_id trong session
        
        Args:
            track_id: Tracking ID
            session_id: Session ID
            so_hieu_ocr: Số hiệu tàu (cập nhật nếu có)
            do_tin_cay_ocr: Confidence OCR (cập nhật nếu có)
            toc_do_tb: Tốc độ trung bình (cập nhật nếu có)
            hinh_anh_path: Đường dẫn ảnh (cập nhật nếu có)
        
        Returns:
            True nếu cập nhật thành công
        """
        with self.lock:
            try:
                df = pd.read_csv(self.csv_path)
                
                # Tìm dòng cuối cùng của track_id trong session này
                mask = (df['track_id'] == track_id) & (df['session_id'] == session_id)
                matching_rows = df[mask]
                
                if matching_rows.empty:
                    print(f">> CSV: Không tìm thấy track_id={track_id} trong session={session_id}")
                    return False
                
                # Lấy index của dòng cuối cùng
                last_idx = matching_rows.index[-1]
                
                # Cập nhật các trường
                if so_hieu_ocr is not None:
                    df.at[last_idx, 'so_hieu_ocr'] = so_hieu_ocr
                if do_tin_cay_ocr is not None:
                    df.at[last_idx, 'do_tin_cay_ocr'] = do_tin_cay_ocr
                if toc_do_tb is not None:
                    df.at[last_idx, 'toc_do_tb'] = toc_do_tb
                if hinh_anh_path is not None:
                    df.at[last_idx, 'hinh_anh_path'] = hinh_anh_path
                
                # Ghi lại CSV
                df.to_csv(self.csv_path, index=False, encoding='utf-8')
                print(f">> CSV: Cập nhật track_id={track_id} thành công")
                return True
                
            except Exception as e:
                print(f">> CSV Error: Lỗi update_log: {e}")
                return False
    
    def get_all_logs(self) -> List[Dict]:
        """
        Lấy tất cả các dòng log từ CSV (sắp xếp theo gio_phat_hien DESC)
        
        Returns:
            List của dictionaries chứa dữ liệu log
        """
        try:
            df = pd.read_csv(self.csv_path)
            if df.empty:
                return []
            
            # Sắp xếp theo gio_phat_hien descending
            df_sorted = df.sort_values('gio_phat_hien', ascending=False)
            return df_sorted.to_dict('records')
            
        except Exception as e:
            print(f">> CSV Error: Lỗi get_all_logs: {e}")
            return []
    
    def get_logs_by_session(self, session_id: str) -> List[Dict]:
        """Lấy tất cả logs của một session"""
        try:
            df = pd.read_csv(self.csv_path)
            df_session = df[df['session_id'] == session_id]
            
            if df_session.empty:
                return []
            
            return df_session.sort_values('gio_phat_hien', ascending=False).to_dict('records')
            
        except Exception as e:
            print(f">> CSV Error: Lỗi get_logs_by_session: {e}")
            return []
    
    def get_logs_by_so_hieu(self, so_hieu: str) -> List[Dict]:
        """Lấy tất cả logs của một tàu (theo so_hieu)"""
        try:
            df = pd.read_csv(self.csv_path)
            df_ship = df[df['so_hieu_ocr'] == so_hieu]
            
            if df_ship.empty:
                return []
            
            return df_ship.sort_values('gio_phat_hien', ascending=False).to_dict('records')
            
        except Exception as e:
            print(f">> CSV Error: Lỗi get_logs_by_so_hieu: {e}")
            return []
    
    def get_log_by_track_id(self, track_id: int, session_id: str) -> Optional[Dict]:
        """Lấy log cuối cùng của một track_id trong session"""
        try:
            df = pd.read_csv(self.csv_path)
            mask = (df['track_id'] == track_id) & (df['session_id'] == session_id)
            matching = df[mask]
            
            if matching.empty:
                return None
            
            # Lấy dòng cuối cùng
            return matching.iloc[-1].to_dict()
            
        except Exception as e:
            print(f">> CSV Error: Lỗi get_log_by_track_id: {e}")
            return None
    
    def delete_old_logs(self, days: int = 30) -> int:
        """
        Xóa các log cũ hơn N ngày
        
        Args:
            days: Số ngày
        
        Returns:
            Số dòng bị xóa
        """
        with self.lock:
            try:
                df = pd.read_csv(self.csv_path)
                df['gio_phat_hien'] = pd.to_datetime(df['gio_phat_hien'])
                
                cutoff_date = datetime.now() - pd.Timedelta(days=days)
                df_filtered = df[df['gio_phat_hien'] >= cutoff_date]
                
                deleted_count = len(df) - len(df_filtered)
                df_filtered.to_csv(self.csv_path, index=False, encoding='utf-8')
                
                print(f">> CSV: Xóa {deleted_count} logs cũ hơn {days} ngày")
                return deleted_count
                
            except Exception as e:
                print(f">> CSV Error: Lỗi delete_old_logs: {e}")
                return 0
    
    def get_csv_path(self) -> str:
        """Lấy đường dẫn đầy đủ của file CSV"""
        return str(self.csv_path)
    
    def get_log_dir(self) -> str:
        """Lấy thư mục chứa log"""
        return str(self.log_dir)


# Singleton instance
_csv_logger_instance: Optional[CSVLogger] = None


def get_csv_logger(log_dir: str = None) -> CSVLogger:
    """Lấy CSV logger (Singleton pattern)"""
    global _csv_logger_instance
    if _csv_logger_instance is None:
        _csv_logger_instance = CSVLogger(log_dir)
    return _csv_logger_instance


def reset_csv_logger():
    """Reset CSV logger (cho testing)"""
    global _csv_logger_instance
    _csv_logger_instance = None
