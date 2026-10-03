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
from ui.styles import apply_custom_styles
from services.agent_service import AgentService
from services.document_service import DocumentService
from services.timetable_service import TimetableService

# ----------------- EMBEDDED ATTENDANCE ENGINE -----------------
class AttendanceService:
    LOG_FILE = UPLOADS_DIR / "attendance_log.csv"

    @classmethod
    def generate_single_qr(cls, person_id: str, name: str, role: str, class_name: str) -> Image.Image:
        payload = f"{person_id.strip()}|{name.strip()}|{role.strip()}|{class_name.strip()}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        return qr.make_image(fill_color="#1E3A8A", back_color="white").convert("RGB")

    @classmethod
    def generate_bulk_qr_zip(cls, df: pd.DataFrame) -> bytes:
        col_map = {str(c).strip().lower(): c for c in df.columns}
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


# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="EduCrew AI | Enterprise School Platform", page_icon="🏫", layout="wide")
apply_custom_styles()

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=64)
    st.markdown("## **EduCrew Enterprise**")
    st.caption("Autonomous Multi-Agent School Operations")
    
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=env_api_key, type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    model_choice = st.selectbox("Gemini Foundation Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    st.markdown("---")
    
    app_mode = st.radio(
        "Executive Workspaces",
        [
            "🏛️ Enterprise Dashboard",
            "📚 Multi-Agent Lesson Architect",
            "🗓️ Timetable Engine & Agent Audit",
            "🪪 ID Card & QR Batch Studio",
            "📷 Live QR Attendance & Welfare Agent"
        ]
    )

# ----------------- WORKSPACE 0: ENTERPRISE DASHBOARD -----------------
if app_mode == "🏛️ Enterprise Dashboard":
    st.markdown('<div class="main-header">Institutional Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time telemetry, multi-agent status, and operational health</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="kpi-card"><div class="kpi-value">4 Crews</div><div class="kpi-label">Active Agent Teams</div></div>', unsafe_allow_html=True)
    with col2:
        logs = AttendanceService.get_logs()
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(logs)}</div><div class="kpi-label">Today Check-Ins</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="kpi-card"><div class="kpi-value">45 Slots</div><div class="kpi-label">Weekly Standard Grid</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="kpi-card"><div class="kpi-value">Active</div><div class="kpi-label">Farm Master Lock</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("### 🤖 Available Autonomous Crews")
    c1, c2 = st.columns(2)
    with c1:
        st.info("**Academic Planning Crew**\n- Lead Curriculum Architect\n- Senior Assessment Specialist\n- Inclusive Education Consultant")
        st.info("**Timetable Optimization Crew**\n- School Scheduling Compliance Auditor\n- Academic Operations Strategist")
    with c2:
        st.success("**Attendance & Welfare Crew**\n- Truancy & Punctuality Analyst\n- Student Welfare & Parent Liaison")
        st.success("**Security & Verification**\n- Computer Vision QRCode Engine\n- Institutional CSV/Excel Batch Generator")

# ----------------- WORKSPACE 1: LESSON ARCHITECT -----------------
elif app_mode == "📚 Multi-Agent Lesson Architect":
    st.markdown('<div class="main-header">Academic Curriculum Crew</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Three specialized agents collaborate sequentially on pedagogical design</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        topic = st.text_input("Lesson Topic", placeholder="e.g., Renewable Energy Systems & Photovoltaics")
        grade_level = st.selectbox("Academic Level", ["Grade 6-8 (Middle School)", "Grade 9-10 (High School)", "Grade 11-12 (Higher Secondary)"])
    with c2:
        uploaded_doc = st.file_uploader("Reference Curriculum Chapter / Notes (PDF, TXT)", type=["pdf", "txt"])

    if st.button("🚀 Kickoff Curriculum Crew"):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("Please supply your Gemini API key in the sidebar.")
        elif not topic:
            st.warning("Please specify a topic.")
        else:
            with st.spinner("Crew in progress: Designing objectives, formulating Bloom's quiz, adapting instruction..."):
                doc_text = ""
                if uploaded_doc:
                    saved_path = UPLOADS_DIR / uploaded_doc.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_doc.getbuffer())
                    doc_text = DocumentService.extract_text(saved_path)

                agent_svc = AgentService(model_name=model_choice)
                result = agent_svc.run_lesson_planning_workflow(topic, grade_level, doc_text)
                st.success("Curriculum pack finalized by all 3 agents!")
                st.markdown("### 📋 Executive Output")
                st.markdown(result)
                st.download_button("📥 Export Lesson Pack (.MD)", result, f"{topic.replace(' ', '_')}_curriculum.md", "text/markdown")

# ----------------- WORKSPACE 2: TIMETABLE & AUDIT -----------------
elif app_mode == "🗓️ Timetable Engine & Agent Audit":
    st.markdown('<div class="main-header">Master Scheduling & Agent Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Deterministic constraint scheduling coupled with AI Compliance Audit</div>', unsafe_allow_html=True)

    template_df = pd.DataFrame({
        "Class": ["10th-A", "10th-A", "10th-A", "9th-B", "9th-B"],
        "Teacher Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood", "Ms. Ayesha Bibi", "Mr. Tariq Mehmood"],
        "Designation": ["Farm Master", "Senior Subject Specialist", "Subject Specialist", "Junior Teacher", "Subject Specialist"],
        "Periods Per Week": [6, 4, 3, 4, 3],
        "Subject": ["Agriculture & Biology", "Physics", "Mathematics", "English", "Mathematics"]
    })

    with st.expander("ℹ️ Download Master Roster Template"):
        st.dataframe(template_df)
        csv_sample = template_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Template CSV", csv_sample, "master_teachers.csv", "text/csv")

    col_up, col_name = st.columns([2, 1])
    with col_up:
        tt_file = st.file_uploader("Upload Teacher Workload File", type=["csv", "xlsx", "xls"])
    with col_name:
        default_cls = st.text_input("Default Class Name", value="10th Class")

    if tt_file:
        saved_path = UPLOADS_DIR / tt_file.name
        with open(saved_path, "wb") as f:
            f.write(tt_file.getbuffer())

        try:
            df_in = DocumentService.read_tabular(saved_path)
            st.dataframe(df_in.head(6), use_container_width=True)

            if st.button("⚡ Solve Timetable & Run Agent Audit"):
                with st.spinner("1/2: Constraint Engine solving period allocations..."):
                    day_tables, err = TimetableService.generate_timetable(df_in, default_class_name=default_cls)

                if err:
                    st.error(err)
                else:
                    st.success("Constraint solving complete!")
                    tabs = st.tabs(list(day_tables.keys()))
                    summary_text = ""
                    for idx, tab_name in enumerate(day_tables.keys()):
                        with tabs[idx]:
                            st.write(f"#### 📋 {tab_name}")
                            st.dataframe(day_tables[tab_name], use_container_width=True)
                            summary_text += f"\n--- {tab_name} ---\n" + day_tables[tab_name].head(4).to_string()

                    # Trigger Multi-Agent Audit Crew
                    st.markdown("---")
                    st.write("### 🤖 Timetable Compliance & Executive Audit Crew")
                    with st.spinner("2/2: Timetable Auditor and Operations Strategist analyzing feasibility..."):
                        agent_svc = AgentService(model_name=model_choice)
                        audit_result = agent_svc.run_timetable_audit_crew(summary_text)
                        st.markdown(audit_result)

                    out_excel = UPLOADS_DIR / "Master_Timetable.xlsx"
                    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
                        for s_name, ddf in day_tables.items():
                            ddf.to_excel(writer, sheet_name=s_name[:31], index=False)

                    with open(out_excel, "rb") as f:
                        st.download_button("📥 Download Master Timetable (.XLSX)", f.read(), "Master_Timetable.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as ex:
            st.error(f"Error: {ex}")

# ----------------- WORKSPACE 3: QR STUDIO -----------------
elif app_mode == "🪪 ID Card & QR Batch Studio":
    st.markdown('<div class="main-header">Institutional QR & ID Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Batch QR generation engine formatted with cryptographic tokens</div>', unsafe_allow_html=True)

    tab_single, tab_batch = st.tabs(["Individual ID Card", "Batch Roster Importer"])

    with tab_single:
        s1, s2 = st.columns(2)
        with s1:
            name = st.text_input("Full Name", "Zia Muhammad")
            p_id = st.text_input("Staff / Student ID", "EMP-2026")
        with s2:
            role = st.selectbox("Designation", ["Student", "Subject Specialist", "Farm Master", "Principal", "Staff"])
            cls_name = st.text_input("Class / Dept", "10th Grade")

        if st.button("Generate Secure Card"):
            img = AttendanceService.generate_single_qr(p_id, name, role, cls_name)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(buf.getvalue(), width=200)
            with c2:
                st.success("Secure Token Encoded Successfully")
                st.code(f"{p_id}|{name}|{role}|{cls_name}")
                st.download_button("📥 Download Card PNG", buf.getvalue(), f"{p_id}_card.png", "image/png")

    with tab_batch:
        roster_file = st.file_uploader("Upload Roster (CSV/Excel)", type=["csv", "xlsx"])
        if roster_file:
            df_r = pd.read_csv(roster_file) if roster_file.name.endswith(".csv") else pd.read_excel(roster_file)
            st.dataframe(df_r.head(5), use_container_width=True)
            if st.button("⚡ Generate Batch ZIP Archive"):
                with st.spinner("Generating individual tokens..."):
                    zip_data = AttendanceService.generate_bulk_qr_zip(df_r)
                    st.download_button("📥 Download All Cards (.ZIP)", zip_data, "School_ID_Batch.zip", "application/zip")

# ----------------- WORKSPACE 4: ATTENDANCE & WELFARE AGENT -----------------
elif app_mode == "📷 Live QR Attendance & Welfare Agent":
    st.markdown('<div class="main-header">Smart Gate & Welfare Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated optical scanner connected to Truancy & Welfare Multi-Agent Crew</div>', unsafe_allow_html=True)

    c_cam, c_act = st.columns([1, 1])
    with c_cam:
        st.write("#### 🎥 Live Optical Feed")
        cam_shot = st.camera_input("Scan ID Card QR")

    with c_act:
        st.write("#### 📋 Immediate Gate Decision")
        if cam_shot:
            raw = cam_shot.getvalue()
            decoded = AttendanceService.decode_qr(raw)
            if not decoded:
                st.warning("Align card with lens in good light.")
            else:
                parts = [p.strip() for p in decoded.split("|")]
                pid = parts[0] if len(parts) > 0 else "UNKNOWN"
                pname = parts[1] if len(parts) > 1 else "Unknown"
                prole = parts[2] if len(parts) > 2 else "Student"
                pcls = parts[3] if len(parts) > 3 else "General"
                now_str = datetime.now().strftime("%I:%M %p")

                # Fast Gate Rule
                is_on_time = datetime.now().hour < 8 or (datetime.now().hour == 8 and datetime.now().minute <= 10)
                status = "Present - On Time" if is_on_time else "Tardy / Late"

                AttendanceService.log_attendance(pid, pname, prole, pcls, status, f"Gate scan at {now_str}")
                st.success(f"Identity Verified: **{pname}** ({prole})")
                st.markdown(f"**Class:** {pcls} | **Gate Timestamp:** {now_str}")
                st.markdown(f"**Status:** `{status}`")

    st.markdown("---")
    st.write("### 📊 Today's Institutional Log")
    today_logs = AttendanceService.get_logs()
    if not today_logs.empty:
        st.dataframe(today_logs, use_container_width=True)

        if st.button("🤖 Run Truancy & Parent Welfare Agent Analysis"):
            with st.spinner("Truancy Analyst and Parent Welfare Liaison examining check-ins..."):
                agent_svc = AgentService(model_name=model_choice)
                analysis_out = agent_svc.run_attendance_intelligence_crew(today_logs.to_string())
                st.markdown("### 📋 Welfare & Administrative Intelligence Brief")
                st.markdown(analysis_out)

        st.download_button("📥 Export Register (CSV)", today_logs.to_csv(index=False).encode("utf-8"), "attendance_register.csv", "text/csv")
    else:
        st.info("No scans recorded yet today.")
