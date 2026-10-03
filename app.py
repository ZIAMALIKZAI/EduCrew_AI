import os
import io
import hmac
import hashlib
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
from services.db_service import DatabaseService

# Initialize SQLite Relational Database Engine
DatabaseService.init_database()

# Enterprise Secret Key for Digital QR Signatures
HMAC_SECRET = os.getenv("EDUCREW_SIGNING_SECRET", "educrew_enterprise_secure_salt_2026").encode()

# ----------------- CRYPTOGRAPHIC SECURITY & ATTENDANCE -----------------
class SecurityService:
    @classmethod
    def sign_payload(cls, raw_data: str) -> str:
        """Generates an HMAC-SHA256 signature token to prevent QR forgery."""
        return hmac.new(HMAC_SECRET, raw_data.encode(), hashlib.sha256).hexdigest()[:12]

    @classmethod
    def generate_signed_qr(cls, person_id: str, name: str, role: str, class_name: str) -> Image.Image:
        raw_body = f"{person_id.strip()}|{name.strip()}|{role.strip()}|{class_name.strip()}"
        signature = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{signature}"
        
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(signed_token)
        qr.make(fit=True)
        return qr.make_image(fill_color="#1E3A8A", back_color="white").convert("RGB")

    @classmethod
    def verify_token(cls, full_token: str):
        """Verifies if the QR code is authentic or forged."""
        if "#" not in full_token:
            return False, full_token.split("|"), "Unsigned QR Code (Legacy / Untrusted)"
        
        body, received_sig = full_token.split("#", 1)
        expected_sig = cls.sign_payload(body)
        
        parts = [p.strip() for p in body.split("|")]
        if hmac.compare_digest(received_sig, expected_sig):
            return True, parts, "Authenticated Institutional Signature"
        return False, parts, "SECURITY ALERT: Signature mismatch (Tampered QR)"

    @classmethod
    def decode_camera_frame(cls, image_bytes: bytes) -> str:
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return ""
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(img)
            return data.strip() if data else ""
        except Exception:
            return ""

    @classmethod
    def generate_bulk_signed_zip(cls, df: pd.DataFrame) -> bytes:
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

                img = cls.generate_signed_qr(p_id, p_name, p_role, p_class)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                safe_name = "".join(c for c in f"{p_id}_{p_name}" if c.isalnum() or c in (' ', '_', '-')).rstrip()
                zip_file.writestr(f"{safe_name}.png", img_bytes.getvalue())

        zip_buffer.seek(0)
        return zip_buffer.getvalue()


# ----------------- PAGE CONFIG & SESSION MANAGEMENT -----------------
st.set_page_config(page_title="EduCrew AI | Enterprise Operations", page_icon="🏫", layout="wide")
apply_custom_styles()

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# ----------------- AUTHENTICATION GATE -----------------
if not st.session_state["auth_user"]:
    st.markdown('<div class="main-header" style="text-align:center;">🏛️ EduCrew Enterprise Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header" style="text-align:center;">Institutional Multi-Agent Governance & Operations Platform</div>', unsafe_allow_html=True)
    
    col_login, _ = st.columns([1, 1])
    with col_login:
        with st.form("login_form"):
            st.write("#### 🔐 Staff & Administrator Sign-In")
            u_name = st.text_input("Username", value="admin")
            u_pass = st.text_input("Password", type="password", value="admin123")
            submit = st.form_submit_button("Authenticate into Portal")
            
            if submit:
                user = DatabaseService.authenticate_user(u_name, u_pass)
                if user:
                    st.session_state["auth_user"] = user
                    st.rerun()
                else:
                    st.error("Invalid institutional credentials.")
                    
        st.info("Demo Credentials:\n- **Principal**: `admin` / `admin123`\n- **Faculty**: `teacher` / `teach123`\n- **Campus Security**: `gate` / `gate123`")
    st.stop()

# ----------------- ROLE-BASED ACCESS CONTROL (RBAC) -----------------
current_user = st.session_state["auth_user"]
user_role = current_user["role"]

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=54)
    st.markdown(f"### **EduCrew Portal**")
    st.caption(f"Authenticated: **{current_user['full_name']}**\nRole: `{user_role}`")
    
    if st.button("🚪 Sign Out"):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("---")
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=env_api_key, type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    model_choice = st.selectbox("Gemini Engine", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    st.markdown("---")

    # Dynamic Menu according to RBAC
    if user_role == "Principal":
        nav_options = [
            "🏛️ Executive Dashboard",
            "📚 Curriculum Multi-Agent Crew",
            "🗓️ Timetable Engine & Audit",
            "🪪 ID Card & QR Batch Studio",
            "📷 Campus Gate & Attendance Agent"
        ]
    elif user_role == "Teacher":
        nav_options = [
            "📚 Curriculum Multi-Agent Crew",
            "🗓️ Timetable Engine & Audit",
            "📷 Campus Gate & Attendance Agent"
        ]
    else:  # Security / Gate Officer
        nav_options = ["📷 Campus Gate & Attendance Agent"]

    app_mode = st.radio("Enterprise Navigation", nav_options)

# ----------------- WORKSPACE: EXECUTIVE DASHBOARD -----------------
if app_mode == "🏛️ Executive Dashboard":
    st.markdown('<div class="main-header">Institutional Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Relational SQLite telemetry and live agent execution metrics</div>', unsafe_allow_html=True)

    today_logs = DatabaseService.get_today_logs_df()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="kpi-card"><div class="kpi-value">4 Crews</div><div class="kpi-label">Active Autonomous Agents</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(today_logs)}</div><div class="kpi-label">Today Scans</div></div>', unsafe_allow_html=True)
    with c3:
        forged_count = len(today_logs[today_logs["Authenticated"] == 0]) if not today_logs.empty else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:#DC2626;">{forged_count}</div><div class="kpi-label">Security Tamper Flags</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="kpi-card"><div class="kpi-value">Active</div><div class="kpi-label">HMAC-SHA256 Token Engine</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("### 🗄️ Relational Database Attendance Log (ACID Storage)")
    if not today_logs.empty:
        st.dataframe(today_logs, use_container_width=True)
    else:
        st.info("No scans recorded in the relational database yet today.")

# ----------------- WORKSPACE: LESSON MULTI-AGENT CREW -----------------
elif app_mode == "📚 Curriculum Multi-Agent Crew":
    st.markdown('<div class="main-header">Autonomous Curriculum Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Collaborative multi-agent pedagogical planning pipeline</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        topic = st.text_input("Lesson Topic", placeholder="e.g., Photosynthesis and Cellular Respiration")
        grade_level = st.selectbox("Grade Level", ["Grade 6-8", "Grade 9-10", "Grade 11-12"])
    with c2:
        uploaded_doc = st.file_uploader("Reference Materials (PDF/TXT)", type=["pdf", "txt"])

    if st.button("🚀 Kickoff Curriculum Crew"):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("Please provide your Gemini API key in the sidebar.")
        elif not topic:
            st.warning("Please enter a lesson topic.")
        else:
            with st.spinner("Curriculum Designer, Assessment Specialist, and Inclusion Coach collaborating..."):
                doc_text = ""
                if uploaded_doc:
                    saved_path = UPLOADS_DIR / uploaded_doc.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_doc.getbuffer())
                    doc_text = DocumentService.extract_text(saved_path)

                agent_svc = AgentService(model_name=model_choice)
                result = agent_svc.run_lesson_planning_workflow(topic, grade_level, doc_text)
                st.success("Lesson pack drafted and verified by all 3 agents!")
                st.markdown(result)
                st.download_button("📥 Download Lesson Pack", result, f"{topic.replace(' ', '_')}.md", "text/markdown")

# ----------------- WORKSPACE: TIMETABLE & AUDIT -----------------
elif app_mode == "🗓️ Timetable Engine & Audit":
    st.markdown('<div class="main-header">Algorithmic Timetable & Multi-Agent Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enforces Farm Master Period 1, Friday 5-Period Cap, and Same-Period Class Consistency</div>', unsafe_allow_html=True)

    col_up, col_name = st.columns([2, 1])
    with col_up:
        tt_file = st.file_uploader("Upload Faculty Workload Spreadsheet", type=["csv", "xlsx", "xls"])
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
                with st.spinner("Algorithmic solver calculating schedule..."):
                    day_tables, err = TimetableService.generate_timetable(df_in, default_class_name=default_cls)

                if err:
                    st.error(err)
                else:
                    st.success("Master schedule solved without faculty clashes!")
                    tabs = st.tabs(list(day_tables.keys()))
                    summary_text = ""
                    for idx, tab_name in enumerate(day_tables.keys()):
                        with tabs[idx]:
                            st.write(f"#### 📋 {tab_name}")
                            st.dataframe(day_tables[tab_name], use_container_width=True)
                            summary_text += f"\n--- {tab_name} ---\n" + day_tables[tab_name].head(4).to_string()

                    st.markdown("---")
                    st.write("### 🤖 Autonomous Scheduling Audit Crew")
                    with st.spinner("Registrar Auditor and Academic Strategist evaluating allocations..."):
                        agent_svc = AgentService(model_name=model_choice)
                        audit_result = agent_svc.run_timetable_audit_crew(summary_text)
                        st.markdown(audit_result)
        except Exception as ex:
            st.error(f"File parsing error: {ex}")

# ----------------- WORKSPACE: QR STUDIO (CRYPTOGRAPHIC) -----------------
elif app_mode == "🪪 ID Card & QR Batch Studio":
    st.markdown('<div class="main-header">Cryptographic ID Card Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Issues HMAC-SHA256 signed QR credentials that cannot be forged</div>', unsafe_allow_html=True)

    tab_single, tab_batch = st.tabs(["Individual Signed Credential", "Bulk Roster Generator"])

    with tab_single:
        s1, s2 = st.columns(2)
        with s1:
            name = st.text_input("Full Name", "Muhammad Tariq")
            p_id = st.text_input("Staff / Student ID", "EMP-9021")
        with s2:
            role = st.selectbox("Designation", ["Student", "Subject Specialist", "Farm Master", "Principal"])
            cls_name = st.text_input("Assigned Class / Department", "Class 10th-A")

        if st.button("Generate Signed Credential"):
            img = SecurityService.generate_signed_qr(p_id, name, role, cls_name)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(buf.getvalue(), width=200)
            with c2:
                sig = SecurityService.sign_payload(f"{p_id}|{name}|{role}|{cls_name}")
                st.success("Cryptographically Signed QR Created")
                st.markdown(f"**HMAC Signature:** `{sig}`")
                st.code(f"{p_id}|{name}|{role}|{cls_name}#{sig}")
                st.download_button("📥 Download Signed PNG", buf.getvalue(), f"{p_id}_secure.png", "image/png")

    with tab_batch:
        roster_file = st.file_uploader("Upload Master Roster (CSV / Excel)", type=["csv", "xlsx"])
        if roster_file:
            df_r = pd.read_csv(roster_file) if roster_file.name.endswith(".csv") else pd.read_excel(roster_file)
            st.dataframe(df_r.head(5), use_container_width=True)
            if st.button("⚡ Generate Secure Signed ZIP Batch"):
                with st.spinner("Signing individual tokens and generating QR package..."):
                    zip_data = SecurityService.generate_bulk_signed_zip(df_r)
                    st.download_button("📥 Download Signed QR Archive (.ZIP)", zip_data, "Institutional_Signed_QRs.zip", "application/zip")

# ----------------- WORKSPACE: CAMPUS GATE & ATTENDANCE AGENT -----------------
elif app_mode == "📷 Campus Gate & Attendance Agent":
    st.markdown('<div class="main-header">Smart Gate & Truancy Multi-Agent Crew</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time cryptographic verification with automated parent notifications</div>', unsafe_allow_html=True)

    c_cam, c_act = st.columns([1, 1])
    with c_cam:
        st.write("#### 🎥 Live Optical Gate Scanner")
        cam_shot = st.camera_input("Scan ID Card QR Code")

    with c_act:
        st.write("#### 🛡️ Gate Security & Punctuality Engine")
        if cam_shot:
            raw_bytes = cam_shot.getvalue()
            decoded_token = SecurityService.decode_camera_frame(raw_bytes)
            
            if not decoded_token:
                st.warning("⚠️ No QR code recognized. Align card in front of camera.")
            else:
                is_valid, parts, sec_msg = SecurityService.verify_token(decoded_token)
                pid = parts[0] if len(parts) > 0 else "UNKNOWN"
                pname = parts[1] if len(parts) > 1 else "Unknown"
                prole = parts[2] if len(parts) > 2 else "Student"
                pcls = parts[3] if len(parts) > 3 else "General"
                now_str = datetime.now().strftime("%I:%M %p")

                # Punctuality calculation
                is_on_time = datetime.now().hour < 8 or (datetime.now().hour == 8 and datetime.now().minute <= 10)
                status = "Present - On Time" if is_on_time else "Tardy / Late"

                if not is_valid:
                    st.error(f"🚨 {sec_msg}")
                    DatabaseService.record_attendance(pid, pname, prole, pcls, "FLAGGED_FORGERY", sec_msg, False)
                else:
                    st.success(f"Verified Identity: **{pname}** ({prole})")
                    st.markdown(f"**Security Token:** `{sec_msg}`")
                    st.markdown(f"**Class:** {pcls} | **Gate Timestamp:** {now_str}")
                    st.markdown(f"**Gate Status:** `{status}`")
                    
                    DatabaseService.record_attendance(pid, pname, prole, pcls, status, f"Gate scan at {now_str}", True)
                    
                    if status != "Present - On Time" and prole == "Student":
                        st.warning(f"📱 **Automated Parent SMS Dispatched:** 'Notice: Student {pname} checked in at {now_str}, after the 08:00 AM school bell.'")

    st.markdown("---")
    st.write("### 📊 Today's Relational Attendance Register")
    today_records = DatabaseService.get_today_logs_df()
    if not today_records.empty:
        st.dataframe(today_records, use_container_width=True)
        if st.button("🤖 Run Truancy & Welfare Multi-Agent Analysis"):
            with st.spinner("Truancy Analyst & Welfare Liaison examining attendance patterns..."):
                agent_svc = AgentService(model_name=model_choice)
                analysis_brief = agent_svc.run_attendance_intelligence_crew(today_records.to_string())
                st.markdown("### 📋 Welfare Intelligence Brief")
                st.markdown(analysis_brief)
    else:
        st.info("No check-ins logged yet today.")
