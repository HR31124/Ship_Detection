# src/utils/connect.py
import psycopg2
from psycopg2 import pool
from typing import Optional

class DatabaseConnection:
    _instance = None
    _pool: Optional[pool.SimpleConnectionPool] = None
    _first_connect = True   # ← Chỉ in 1 lần

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.host = "aws-1-ap-northeast-1.pooler.supabase.com"
            self.port = 6543
            self.database = "postgres"
            self.user = "postgres.eokqwlzctiqqnszgywsf"
            self.password = "Ship$2004&datn"

            # Tạo pool chỉ 1 lần (tối đa 10 kết nối)
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=self.host,
                    port=self.port,
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                    sslmode="require"
                )
                if self._first_connect:
                    print(">> ✅ Connected Supabase (Pooler 6543) - Pool created!")
                    self._first_connect = False
            except Exception as e:
                print(f">> ❌ Lỗi tạo Pool Supabase: {e}")
                self._pool = None

    def get_connection(self):
        if self._pool is None:
            print(">> ❌ Pool chưa được tạo!")
            return None
        try:
            return self._pool.getconn()
        except Exception as e:
            print(f">> ❌ Lỗi lấy connection từ pool: {e}")
            return None

    def put_connection(self, conn):
        if self._pool and conn:
            try:
                self._pool.putconn(conn)
            except:
                pass

    def close_all(self):
        if self._pool:
            try:
                self._pool.closeall()
                print(">> 🔌 Đã đóng toàn bộ Pool Supabase")
            except:
                pass
            self._pool = None

# ====================== CÁC HÀM PUBLIC ======================
db = DatabaseConnection()

def get_db_connection():
    return db.get_connection()

def close_db_connection():
    db.close_all()

# Hàm tiện ích (dùng trong with)
def release_connection(conn):
    if conn:
        db.put_connection(conn)