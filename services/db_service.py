import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from core.config import BASE_DIR

DB_PATH = BASE_DIR / "data" / "educrew_enterprise.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class DatabaseService:
    @classmethod
    def get_connection(cls):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_database(cls):
        """Initializes relational tables if they do not exist."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        # 1. Users & RBAC
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)

        # 2. Institutional Attendance Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                class_name TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                scan_time TEXT NOT NULL,
                status TEXT NOT NULL,
                remarks TEXT,
                verified_signature INTEGER DEFAULT 1
            )
        """)

        # Seed default administrative credentials if empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)
            """, [
                ("admin", "admin123", "Chief Academic Administrator", "Principal"),
                ("teacher", "teach123", "Senior Faculty Member", "Teacher"),
                ("gate", "gate123", "Campus Gate Controller", "Security")
            ])
            
        conn.commit()
        conn.close()

    @classmethod
    def record_attendance(cls, person_id: str, name: str, role: str, class_name: str, status: str, remarks: str, is_valid_sig: bool):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M:%S %p")
        
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance_logs (person_id, full_name, role, class_name, scan_date, scan_time, status, remarks, verified_signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (person_id, name, role, class_name, date_str, time_str, status, remarks, 1 if is_valid_sig else 0))
        conn.commit()
        conn.close()

    @classmethod
    def get_today_logs_df(cls) -> pd.DataFrame:
        today_str = datetime.now().strftime("%Y-%m-%d")
        conn = cls.get_connection()
        query = "SELECT scan_date AS Date, scan_time AS Time, person_id AS ID, full_name AS Name, role AS Role, class_name AS Class, status AS Status, remarks AS Remarks, verified_signature AS Authenticated FROM attendance_logs WHERE scan_date = ? ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=(today_str,))
        conn.close()
        return df

    @classmethod
    def authenticate_user(cls, username: str, password_raw: str):
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, full_name, role FROM users WHERE username = ? AND password_hash = ?", (username, password_raw))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {"username": user["username"], "full_name": user["full_name"], "role": user["role"]}
        return None
