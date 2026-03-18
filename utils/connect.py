import pyodbc
import os
from typing import Optional


class DatabaseConnection:
    _instance = None
    _conn: Optional[pyodbc.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.server = r'.\SQLEXPRESS'
            self.database = 'shipdb'
            self.driver = 'ODBC Driver 17 for SQL Server'

    def get_connection_string(self) -> str:
        return (
            f'DRIVER={{{self.driver}}};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            'Trusted_Connection=yes;'
        )

    def connect(self) -> Optional[pyodbc.Connection]:
        if self._conn is None or self._conn.closed:
            try:
                self._conn = pyodbc.connect(self.get_connection_string())
                print(">> Kết nối database thành công")
            except pyodbc.Error as e:
                print(f">> Lỗi kết nối database: {e}")
                self._conn = None
        return self._conn

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            print(">> Đã đóng kết nối database")
            self._conn = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self.close()


db = DatabaseConnection()


def get_db_connection() -> Optional[pyodbc.Connection]:
    return db.connect()


def close_db_connection():
    db.close()


def with_connection():
    with DatabaseConnection() as conn:
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            print(cursor.fetchone())