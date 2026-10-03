import os
import io
import zipfile
import cv2
import numpy as np
import qrcode
from PIL import Image
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from core.config import UPLOADS_DIR
from core.gemini import get_llm
from ui.styles import apply_custom_styles
from services.agent_service import AgentService
from services.document_service import DocumentService
from services.timetable_service import TimetableService

# ----------------- ATTENDANCE & QR UTILITIES -----------------
class AttendanceService:
    LOG_FILE = UPLOADS_DIR / "attendance_log.csv"

    @classmethod
    def generate_single_qr(cls, person_id: str, name: str, role: str, class_name: str) -> Image.Image:
        """Encodes standard EduCrew format (ID|Name|Role|Class) into a QR image."""
        payload = f"{person_id.strip()}|{name.strip()}|{role.strip()}|{class_name.strip()}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")

    @classmethod
    def generate_bulk_qr_zip(cls, df: pd.DataFrame) -> bytes:
        """Parses a roster dataframe and bundles all generated QR codes into a ZIP file."""
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        # Flexible column resolution
        id_col = next((col_map[c] for c in col_map if "id" in c or "roll" in c), None)
        name_col = next((col_map[c] for c in col_map if "name" in c), None)
        role_col = next((col_map[c] for c in col_map if "role" in c or "designation" in c), None)
        class_col = next((col_map[c] for c in col_map if "class" in c or "grade" in c), None)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, row in df.iterrows():
                p_id = str(row[id_col]).strip() if id_col else f"ID_{idx+1}"
                p_name = str(row[name_col]).strip() if name_col else f"Person_{idx+1}"
                p_role = str(row[role_col]).strip() if role_col else "Student"
                p_class = str(row[class_col]).strip() if class_col else "General"

                img = cls.generate_single_qr(p_id, p_name, p_role, p_class)
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")
                
                safe_name = "".join(c for c in f"{p_id}_{p_name}" if c.isalnum() or c in (' ', '_', '-')).rstrip()
                zip_file.writestr(f"{safe_name}.png", img_byte_arr.getvalue())

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

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
            try:
                df = pd.read_csv(cls.LOG_FILE)
                df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            except Exception:
                df = pd.DataFrame([record])
        else:
            df = pd.DataFrame([record])
        df.to_csv(cls.LOG_FILE, index=False)
        return df

    @classmethod
    def get_logs(cls) -> pd.DataFrame:
        if cls.LOG_FILE.exists():
            try:
                return pd.read_csv(cls.LOG_FILE)
            except Exception:
                pass
        return pd.DataFrame(columns=["Date", "Time", "ID", "Name", "Role", "Class", "Status", "Remarks"])

    @classmethod
    def evaluate_attendance_with_ai(cls, person_id: str, name: str, role: str, class_name: str, scan_time_str: str) -> dict:
        try:
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
            status, note, sms = "Present", "Checked in successfully.", "None"
            for line in text.split("\n"):
                if line.startswith("STATUS:"):
                    status = line.replace("STATUS:", "").strip()
                elif line.startswith("NOTE:"):
                    note = line.replace("NOTE:", "").strip()
                elif line.startswith("SMS:"):
                    sms = line.replace("SMS:", "").strip()
            return {"status": status, "note": note, "sms": sms}
        except Exception:
            return {"status": "Present (Logged Offline)", "note": f"System recorded at {scan_time_str}", "sms": "None"}


# ----------------- APPLICATION LAYOUT -----------------
st.set_page_config(
    page_title="EduCrew AI - Autonomous School Assistant",
    page_icon="🎓",
    layout="wide"
)

apply_custom_styles()

with st.sidebar:
    st.title("⚙️ EduCrew Settings")
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=env_api_key, type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    model_choice = st.selectbox("Gemini Engine", options=["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    st.markdown("---")
    app_mode = st.radio(
        "Select Capability",
        [
            "Multi-Agent Lesson & Quiz Architect",
            "Automated Timetable Generator",
            "🪪 ID Card & QR Code Generator",
            "Live QR Attendance & Agent Monitor"
        ]
    )

st.markdown('<div class="main-header">🎓 EduCrew AI: Multi-Agent Teacher Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Pedagogical Planning, Timetable Engines, Smart QR Generation & Agentic Attendance</div>', unsafe_allow_html=True)

# ----------------- MODULE 1: LESSON ARCHITECT -----------------
if app_mode == "Multi-Agent Lesson & Quiz Architect":
    st.subheader("🤖 Multi-Agent Curriculum & Assessment Team")
    col1, col2 = st.columns([1, 1])
    with col1:
        topic = st.text_input("Lesson Topic", placeholder="e.g., Photosynthesis and Cellular Respiration")
        grade_level = st.selectbox("Grade Level", ["Grade 6-8 (Middle School)", "Grade 9-10 (High School)", "Grade 11-12 (College Prep)"])
    with col2:
        uploaded_doc = st.file_uploader("Optional: Reference Document (PDF, TXT)", type=["pdf", "txt"])

    if st.button("🚀 Run Multi-Agent Crew"):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("Please supply your Gemini API key in the sidebar.")
        elif not topic:
            st.warning("Please specify a topic.")
        else:
            with st.spinner("Agents are collaborating on your lesson pack..."):
                doc_text = ""
                if uploaded_doc:
                    saved_path = UPLOADS_DIR / uploaded_doc.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_doc.getbuffer())
                    doc_text = DocumentService.extract_text(saved_path)

                agent_svc = AgentService(model_name=model_choice)
                result = agent_svc.run_lesson_planning_workflow(topic, grade_level, doc_text)
                st.success("Lesson pack created successfully!")
                st.markdown("### 📋 Crew Output")
                st.markdown(result)
                st.download_button(
                    label="📥 Download as Markdown",
                    data=result,
                    file_name=f"{topic.replace(' ', '_')}_lesson_pack.md",
                    mime="text/markdown"
                )

# ----------------- MODULE 2: TIMETABLE GENERATOR -----------------
elif app_mode == "Automated Timetable Generator":
    st.subheader("📅 School Timetable Generator (With Class Names & Same-Period Timing)")
    template_df = pd.DataFrame({
        "Class": ["10th-A", "10th-A", "10th-A", "9th-B", "9th-B"],
        "Teacher Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood", "Ms. Ayesha Bibi", "Mr. Tariq Mehmood"],
        "Designation": ["Farm Master", "Senior Subject Specialist", "Subject Specialist", "Junior Teacher", "Subject Specialist"],
        "Periods Per Week": [6, 4, 3, 4, 3],
        "Subject": ["Agriculture & Biology", "Physics", "Mathematics", "English", "Mathematics"]
    })

    with st.expander("ℹ️ Expected File Format (Preview & Download Sample CSV)"):
        st.dataframe(template_df)
        csv_sample = template_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Sample CSV with Class Column", csv_sample, "sample_teachers_with_class.csv", "text/csv")

    col_upload, col_fallback = st.columns([2, 1])
    with col_upload:
        timetable_file = st.file_uploader("Upload Teachers Data File", type=["csv", "xlsx", "xls"])
    with col_fallback:
        default_cls = st.text_input("Default Class Name (if file has no Class column)", value="10th Class")

    if timetable_file:
        saved_tt_path = UPLOADS_DIR / timetable_file.name
        with open(saved_tt_path, "wb") as f:
            f.write(timetable_file.getbuffer())

        try:
            df_in = DocumentService.read_tabular(saved_tt_path)
            st.write("Loaded Data Preview:")
            st.dataframe(df_in.head(8), use_container_width=True)

            if st.button("⚡ Generate Weekly Timetable"):
                with st.spinner("Generating schedules and resolving conflicts..."):
                    day_tables, err = TimetableService.generate_timetable(df_in, default_class_name=default_cls)
                    if err:
                        st.error(err)
                    else:
                        st.success("Timetable generated successfully with all Class assignments!")
                        tabs = st.tabs(list(day_tables.keys()))
                        for idx, tab_name in enumerate(day_tables.keys()):
                            with tabs[idx]:
                                st.write(f"### 📋 {tab_name}")
                                st.dataframe(day_tables[tab_name], use_container_width=True)

                        output_excel = UPLOADS_DIR / "Generated_Weekly_Timetable.xlsx"
                        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                            for sheet_name, ddf in day_tables.items():
                                safe_name = sheet_name.replace(":", "-").replace("/", "-")[:31]
                                ddf.to_excel(writer, sheet_name=safe_name, index=False)

                        with open(output_excel, "rb") as f:
                            st.download_button(
                                label="📥 Download Complete Timetable (Excel)",
                                data=f.read(),
                                file_name="Weekly_School_Timetable.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        except Exception as ex:
            st.error(f"Error parsing file: {ex}")

# ----------------- MODULE 3: QR CODE GENERATOR (SINGLE & BULK) -----------------
elif app_mode == "🪪 ID Card & QR Code Generator":
    st.subheader("🪪 Generate Attendance QR Codes & Cards")
    st.write("Create QR codes encoded in the standard EduCrew format (`ID|Name|Role|Class`) for individual people or an entire school roster.")

    gen_tab1, gen_tab2 = st.tabs(["👤 Single Student/Teacher QR", "📁 Bulk Generate from CSV / Excel"])

    with gen_tab1:
        st.write("#### Create Individual QR Code")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            s_name = st.text_input("Full Name", value="Muhammad Ali")
            s_id = st.text_input("Roll No / Staff ID", value="S-1042")
        with s_col2:
            s_role = st.selectbox("Role", ["Student", "Teacher", "Staff", "Farm Master"])
            s_class = st.text_input("Class / Department", value="Class 10th-A")

        if st.button("Generate QR Code"):
            img = AttendanceService.generate_single_qr(s_id, s_name, s_role, s_class)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            
            c_preview, c_meta = st.columns([1, 2])
            with c_preview:
                st.image(buf.getvalue(), caption=f"QR for {s_name}", width=220)
            with c_meta:
                st.success("QR Code Generated!")
                st.write(f"**Encoded Data:** `{s_id}|{s_name}|{s_role}|{s_class}`")
                st.download_button(
                    label="📥 Download QR Image (PNG)",
                    data=buf.getvalue(),
                    file_name=f"{s_id}_{s_name.replace(' ', '_')}_qr.png",
                    mime="image/png"
                )

    with gen_tab2:
        st.write("#### Bulk Generate from Roster File")
        st.write("Upload a CSV or Excel file containing your school roster. The system reads columns like **ID/Roll**, **Name**, **Role**, and **Class**.")

        sample_roster = pd.DataFrame({
            "ID": ["S101", "S102", "T201", "T202"],
            "Name": ["Hamza Tariq", "Fatima Bibi", "Mr. Ahmad Khan", "Ms. Ayesha"],
            "Role": ["Student", "Student", "Teacher - Farm Master", "Teacher"],
            "Class": ["10th-A", "10th-A", "10th Class", "9th Class"]
        })

        with st.expander("ℹ️ Download Sample Roster Template"):
            st.dataframe(sample_roster)
            st.download_button(
                "Download Sample CSV",
                sample_roster.to_csv(index=False).encode("utf-8"),
                "sample_roster.csv",
                "text/csv"
            )

        roster_file = st.file_uploader("Upload Roster File (CSV, Excel)", type=["csv", "xlsx", "xls"])
        if roster_file:
            try:
                if roster_file.name.endswith(".csv"):
                    df_roster = pd.read_csv(roster_file)
                else:
                    df_roster = pd.read_excel(roster_file)

                st.write(f"Loaded {len(df_roster)} records:")
                st.dataframe(df_roster.head(5), use_container_width=True)

                if st.button("⚡ Bulk Generate All QR Codes (.ZIP)"):
                    with st.spinner("Generating individual QR codes and assembling ZIP archive..."):
                        zip_data = AttendanceService.generate_bulk_qr_zip(df_roster)
                        st.success(f"Generated {len(df_roster)} QR codes successfully!")
                        st.download_button(
                            label="📥 Download All QR Codes (ZIP Archive)",
                            data=zip_data,
                            file_name="School_Roster_QR_Codes.zip",
                            mime="application/zip"
                        )
            except Exception as e:
                st.error(f"Error parsing roster file: {e}")

# ----------------- MODULE 4: ATTENDANCE SCANNER -----------------
elif app_mode == "Live QR Attendance & Agent Monitor":
    st.subheader("📷 Live QR Attendance & Agent Verification")
    st.write("Point an ID card QR code at the camera. The AI Attendance Agent parses the person, checks punctuality against the 8:00 AM bell, and logs the entry.")

    cam_col, result_col = st.columns([1, 1])

    with cam_col:
        st.write("#### 🎥 Live Camera Input")
        camera_image = st.camera_input("Hold ID QR Code in front of camera")

    with result_col:
        st.write("#### 📋 Verification & Agent Actions")
        if camera_image:
            raw_bytes = camera_image.getvalue()
            qr_content = AttendanceService.decode_qr(raw_bytes)

            if not qr_content:
                st.warning("⚠️ No QR code recognized. Ensure the card is held close, stable, and well-lit.")
            else:
                st.success(f"Scanned QR Code: `{qr_content}`")
                parts = [p.strip() for p in qr_content.split("|")]
                
                person_id = parts[0] if len(parts) > 0 else "UNKNOWN"
                name = parts[1] if len(parts) > 1 else "Unknown Person"
                role = parts[2] if len(parts) > 2 else "Student"
                class_name = parts[3] if len(parts) > 3 else "General"
                current_time = datetime.now().strftime("%I:%M %p")

                with st.spinner("AI Attendance Agent evaluating status..."):
                    ai_res = AttendanceService.evaluate_attendance_with_ai(
                        person_id=person_id,
                        name=name,
                        role=role,
                        class_name=class_name,
                        scan_time_str=current_time
                    )

                AttendanceService.log_attendance(
                    person_id=person_id,
                    name=name,
                    role=role,
                    class_name=class_name,
                    status=ai_res["status"],
                    notes=ai_res["note"]
                )

                st.markdown(f"**Name:** {name}")
                st.markdown(f"**Role:** {role} | **Class:** {class_name}")
                st.markdown(f"**Check-in Time:** {current_time}")
                st.markdown(f"**Status:** `{ai_res['status']}`")
                st.info(f"**Admin Note:** {ai_res['note']}")
                
                if ai_res.get("sms") and ai_res["sms"] != "None":
                    st.warning(f"📱 **Automated Parent SMS:** {ai_res['sms']}")

    st.markdown("---")
    st.write("### 📊 Today's Attendance Register")
    current_logs = AttendanceService.get_logs()
    if not current_logs.empty:
        st.dataframe(current_logs, use_container_width=True)
        csv_data = current_logs.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Attendance Sheet (CSV)", csv_data, "daily_attendance.csv", "text/csv")
    else:
        st.info("No attendance recorded yet today.")
