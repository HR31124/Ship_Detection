CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,         
    full_name   VARCHAR(100) NULL,
    role        VARCHAR(50)  NULL DEFAULT 'user',
    ngay_tao    TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password, full_name, role)
VALUES ('admin', '123', 'Quản trị viên', 'admin')
ON CONFLICT (username) DO NOTHING;  


CREATE TABLE ship (
    ship_id         SERIAL PRIMARY KEY,
    so_hieu         VARCHAR(50)  NOT NULL UNIQUE,
    class_name      VARCHAR(100) NULL,
    ten_tau         VARCHAR(150) NULL,
    mo_ta           VARCHAR(500) NULL,
    anh_dai_dien    VARCHAR(255) NULL,
    ngay_tao        TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat   TIMESTAMPTZ  NULL
);

CREATE TABLE shiplog (
    log_id          SERIAL PRIMARY KEY,
    ship_id         INTEGER      NULL,
    track_id        INTEGER      NOT NULL,
    session_id      VARCHAR(150) NULL,
    gio_phat_hien   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    class_name      VARCHAR(100) NULL,
    confidence      FLOAT        NULL,
    toc_do_tb       FLOAT        NULL,
    hinh_anh_path   VARCHAR(255) NULL,
    do_tin_cay_ocr  FLOAT        NULL,
    so_hieu_ocr     VARCHAR(50)  NULL,
    video_source    VARCHAR(255) NULL,
    video_frame     INTEGER      NULL,
    ghi_chu         VARCHAR(500) NULL,

    CONSTRAINT FK_shiplog_ship 
        FOREIGN KEY (ship_id) REFERENCES ship(ship_id)
        ON UPDATE CASCADE 
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_ship_time      ON shiplog (ship_id, gio_phat_hien);
CREATE INDEX IF NOT EXISTS idx_track_session  ON shiplog (track_id, session_id);
CREATE INDEX IF NOT EXISTS idx_sohieu_ocr     ON shiplog (so_hieu_ocr);