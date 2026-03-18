CREATE DATABASE shipdb;
GO

USE shipdb;
GO

-- Bảng người dùng (không hash password)
CREATE TABLE users (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    username    NVARCHAR(50)  NOT NULL UNIQUE,
    password    NVARCHAR(255) NOT NULL,          -- plain text cho demo
    full_name   NVARCHAR(100) NULL,
    role        NVARCHAR(50)  NULL DEFAULT 'user',
    ngay_tao    DATETIME      DEFAULT GETDATE()
);
GO

-- Insert admin mẫu (mật khẩu plain text)
INSERT INTO users (username, password, full_name, role)
VALUES ('admin', '123', 'Quản trị viên', 'admin');
GO

-- Bảng tàu (master data)
CREATE TABLE ship (
    ship_id         INT IDENTITY(1,1) PRIMARY KEY,
    so_hieu         NVARCHAR(50)  NOT NULL UNIQUE,
    class_name      NVARCHAR(100) NULL,
    ten_tau         NVARCHAR(150) NULL,
    mo_ta           NVARCHAR(500) NULL,
    anh_dai_dien    NVARCHAR(255) NULL,
    ngay_tao        DATETIME      DEFAULT GETDATE(),
    ngay_cap_nhat   DATETIME      NULL
);
GO

-- Bảng nhật ký phát hiện (log từ YOLO + OCR)
CREATE TABLE shiplog (
    log_id          INT IDENTITY(1,1) PRIMARY KEY,
    ship_id         INT           NULL,                 -- NULL lúc đầu, update sau khi OCR
    track_id        INT           NOT NULL,
    session_id      NVARCHAR(150) NULL,                 -- tên file video + thời gian hoặc UUID
    gio_phat_hien   DATETIME      NOT NULL DEFAULT GETDATE(),
    class_name      NVARCHAR(100) NULL,
    confidence      FLOAT         NULL,
    toc_do_tb       FLOAT         NULL,
    hinh_anh_path   NVARCHAR(255) NULL,
    do_tin_cay_ocr  FLOAT         NULL,
    so_hieu_ocr     NVARCHAR(50)  NULL,
    video_source    NVARCHAR(255) NULL,
    video_frame     INT           NULL,
    ghi_chu         NVARCHAR(500) NULL,

    CONSTRAINT FK_shiplog_ship 
        FOREIGN KEY (ship_id) REFERENCES ship(ship_id)
        ON UPDATE CASCADE 
        ON DELETE SET NULL,

    INDEX idx_ship_time     (ship_id, gio_phat_hien),
    INDEX idx_track_session (track_id, session_id),
    INDEX idx_sohieu_ocr    (so_hieu_ocr)
);
GO