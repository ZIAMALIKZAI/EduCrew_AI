import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from core.config import UPLOADS_DIR
from core.gemini import get_llm

class AttendanceService:
    LOG_FILE = UPLOADS_DIR / "attendance_log.csv"

    @classmethod
    def decode_qr(cls, image_bytes: bytes) -> str:
        """Decodes QR code from raw image bytes using OpenCV QRCodeDetector."""
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return ""

            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img)
            return data.strip() if data else ""
        except Exception:
            return ""

    @classmethod
    def log_attendance(cls, person_id: str, name: str, role: str, class_name: str, status: str, notes: str) -> pd.DataFrame:
        """Appends an attendance entry to the CSV log."""
        now = datetime.now()
        record = {
            "Date": now.strftime("%Y-%m-%d"),
            "Time": now.strftime("%I:%M:%S %p"),
            "ID": person_id,
            "Name": name,
            "Role": role,
            "Class": class_name,
            "Status": status,
            "Remarks": notes
        }

        if cls.LOG_FILE.exists():
            df = pd.read_csv(cls.LOG_FILE)
            df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        else:
            df = pd.DataFrame([record])

        df.to_csv(cls.LOG_FILE, index=False)
        return df

    @classmethod
    def get_logs(cls) -> pd.DataFrame:
        """Returns the current day's logs."""
        if cls.LOG_FILE.exists():
            return pd.read_csv(cls.LOG_FILE)
        return pd.DataFrame(columns=["Date", "Time", "ID", "Name", "Role", "Class", "Status", "Remarks"])

    @classmethod
    def evaluate_attendance_with_ai(cls, person_id: str, name: str, role: str, class_name: str, scan_time_str: str) -> dict:
        """
        Uses Gemini to evaluate timeliness, compare with school day opening (8:00 AM),
        and draft automated notifications for parents/administration.
        """
        llm = get_llm()
        prompt = f"""
You are an Automated School Attendance Officer.
Details:
- Person Name: {name} (ID: {person_id})
- Role: {role} (Student or Teacher)
- Class: {class_name}
- Current Scan Time: {scan_time_str}
- Official School Gate / Period 1 Start: 08:00 AM

Tasks:
1. Determine Status: 'Present - On Time' (if scanned before or at 08:10 AM), 'Tardy / Late' (if scanned between 08:11 AM and 09:00 AM), or 'Severely Late' (after 09:00 AM).
2. Generate a 1-sentence administrative note.
3. If student is Late, generate a professional 1-sentence SMS alert for their parents.

Output strictly in this format:
STATUS: <Status>
NOTE: <Note>
SMS: <SMS or 'None'>
"""
        response = llm.invoke(prompt)
        text = response.content

        status = "Present"
        note = "Checked in successfully."
        sms = "None"

        for line in text.split("\n"):
            if line.startswith("STATUS:"):
                status = line.replace("STATUS:", "").strip()
            elif line.startswith("NOTE:"):
                note = line.replace("NOTE:", "").strip()
            elif line.startswith("SMS:"):
                sms = line.replace("SMS:", "").strip()

        return {"status": status, "note": note, "sms": sms}
