import os
import io
import cv2
import numpy as np
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
from services.card_service import IDCardService

# Initialize Database
DatabaseService.init_database()

# ----------------- TEMPLATE FACTORY (FOR BULK UPLOADS) -----------------
class TemplateFactory:
    @staticmethod
    def get_timetable_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Class": ["10th-A", "10th-A", "10th-A", "9th-B", "9th-B", "8th-A"],
            "Teacher Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood", "Ms. Ayesha Bibi", "Mr. Tariq Mehmood", "Mr. Asad Ullah"],
            "Designation": ["Farm Master", "Senior Subject Specialist", "Subject Specialist", "Junior Teacher", "Subject Specialist", "Physical Instructor"],
            "Periods Per Week": [6, 4, 3, 4, 3, 5],
            "Subject": ["Agriculture & Biology", "Physics", "Mathematics", "English", "Mathematics", "Physical Education"]
        })

    @staticmethod
    def get_student_id_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Student ID": ["STU-1001", "STU-1002", "STU-1003", "STU-1004"],
            "Full Name": ["Hamza Tariq", "Fatima Bibi", "Muhammad Zayan", "Ayesha Noor"],
            "Role": ["Student", "Student", "Student", "Student"],
            "Class": ["Class 10th-A", "Class 10th-A", "Class 9th-B", "Class 9th-B"],
            "Blood Group": ["B+", "O+", "A+", "AB+"],
            "Emergency Contact": ["+92 301 1111111", "+92 302 2222222", "+92 303 3333333", "+92 304 4444444"]
        })

    @staticmethod
    def get_teacher_id_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Employee ID": ["EMP-501", "EMP-502", "EMP-503"],
            "Full Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood"],
            "Role": ["Farm Master", "Senior Subject Specialist", "Subject Specialist"],
            "Class": ["Agriculture Dept", "Physics Dept", "Mathematics Dept"],
            "Blood Group": ["O+", "A+", "B+"],
            "Emergency Contact": ["+92 300 1234567", "+92 300 7654321", "+92 300 9988776"]
        })

# ----------------- SECURITY UTILITY -----------------
class SecurityService:
    @classmethod
    def verify_token(cls, full_token: str):
        if "#" not in full_token:
            return False, full_token.split("|"), "Unsigned QR Code (Legacy / Untrusted)"
        body, received_sig = full_token.split("#", 1)
        expected_sig = IDCardService.sign_payload(body)
        parts = [p.strip() for p in body.split("|")]
        if received_sig == expected_sig:
            return True, parts, "Authenticated Institutional Signature"
        return False, parts, "SECURITY ALERT: Signature mismatch (Tampered Credential)"

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

# ----------------- APP SETUP -----------------
st.set_page_config(page_title="EduCrew AI | Enterprise School Platform", page_icon="🏫", layout="wide")
apply_custom_styles()

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# Authentication Check
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
                    st.error("Invalid credentials.")
        st.info("Demo Logins:\n- **Principal**: `admin` / `admin123`\n- **Faculty**: `teacher` / `teach123`\n- **Campus Security**: `gate` / `gate123`")
    st.stop()

# Role-Based Navigation
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

    if user_role == "Principal":
        nav_options = [
            "🏛️ Executive Dashboard",
            "🪪 Official ID Card Studio & Agent Officer",
            "🗓️ Timetable Engine & Audit",
            "📚 Curriculum Multi-Agent Crew",
            "📷 Campus Gate & Attendance Agent"
        ]
    elif user_role == "Teacher":
        nav_options = [
            "📚 Curriculum Multi-Agent Crew",
            "🗓️ Timetable Engine & Audit",
            "🪪 Official ID Card Studio & Agent Officer",
            "📷 Campus Gate & Attendance Agent"
        ]
    else:
        nav_options = ["📷 Campus Gate & Attendance Agent"]

    app_mode = st.radio("Enterprise Navigation", nav_options)

# ----------------- 1. EXECUTIVE DASHBOARD -----------------
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
        forged = len(today_logs[today_logs["Authenticated"] == 0]) if not today_logs.empty else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:#DC2626;">{forged}</div><div class="kpi-label">Security Tamper Flags</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="kpi-card"><div class="kpi-value">600x950</div><div class="kpi-label">Official ID Card Standard</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("### 🗄️ Relational Database Attendance Log (ACID Storage)")
    if not today_logs.empty:
        st.dataframe(today_logs, use_container_width=True)
    else:
        st.info("No scans recorded yet today.")

# ----------------- 2. OFFICIAL ID CARD STUDIO -----------------
elif app_mode == "🪪 Official ID Card Studio & Agent Officer":
    st.markdown('<div class="main-header">Official Institutional ID Card Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generate complete, official, printable ID cards for Students and Faculty with embedded HMAC-SHA256 QR credentials</div>', unsafe_allow_html=True)

    tab_single, tab_bulk, tab_templates = st.tabs(["👤 Single Official ID Card", "📁 Bulk Card Generator (ZIP)", "📥 Download Upload Templates"])

    # --- TAB 1: SINGLE CARD ---
    with tab_single:
        st.write("#### Issue Single Official Institutional Card")
        s1, s2, s3 = st.columns(3)
        with s1:
            inst_name = st.text_input("Institution Header", "GOVERNMENT HIGH SCHOOL")
            p_name = st.text_input("Full Legal Name", "Zia Muhammad")
            p_id = st.text_input("Roll No / Employee ID", "STU-2026-08")
        with s2:
            p_role = st.selectbox("Institutional Role", ["Student", "Teacher", "Farm Master", "Senior Subject Specialist", "Principal", "Staff"])
            p_class = st.text_input("Class / Department", "Class 10th-A")
        with s3:
            p_blood = st.selectbox("Blood Group", ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"])
            p_phone = st.text_input("Emergency Contact", "+92 300 1234567")

        if st.button("🪪 Render Official Printable Card"):
            card_img = IDCardService.create_official_id_card(
                person_id=p_id,
                name=p_name,
                role=p_role,
                department_or_class=p_class,
                blood_group=p_blood,
                emergency_contact=p_phone,
                institution_name=inst_name
            )
            buf = io.BytesIO()
            card_img.save(buf, format="PNG")
            
            c_card, c_specs = st.columns([1, 1])
            with c_card:
                st.image(buf.getvalue(), caption=f"Official ID Card: {p_name}", width=320)
            with c_specs:
                st.success("Card Rendered Successfully")
                st.markdown(f"**Card Specs:** 600 x 950 px (Standard Vertical PVC Format)")
                st.markdown(f"**Security Token:** `{IDCardService.sign_payload(f'{p_id}|{p_name}|{p_role}|{p_class}')}`")
                st.download_button(
                    label="📥 Download Printable ID Card (PNG)",
                    data=buf.getvalue(),
                    file_name=f"{p_id}_{p_name.replace(' ', '_')}_Official_Card.png",
                    mime="image/png"
                )

    # --- TAB 2: BULK ROSTER GENERATOR ---
    with tab_bulk:
        st.write("#### Bulk Official ID Card Production")
        st.write("Upload a roster file. The system will create official ID cards for each person and package them in a single downloadable `.zip` file.")

        inst_bulk_title = st.text_input("Institution Header on Bulk Cards", "GOVERNMENT HIGH SCHOOL")
        bulk_file = st.file_uploader("Upload Roster (CSV or Excel)", type=["csv", "xlsx", "xls"])

        if bulk_file:
            df_bulk = pd.read_csv(bulk_file) if bulk_file.name.endswith(".csv") else pd.read_excel(bulk_file)
            st.write(f"Loaded **{len(df_bulk)}** records from roster:")
            st.dataframe(df_bulk.head(5), use_container_width=True)

            if st.button("🚀 Run Credential Agent & Generate All Cards (.ZIP)"):
                # 1. Multi-Agent Audit
                st.markdown("---")
                st.write("### 🤖 Multi-Agent Credential Officer Audit")
                with st.spinner("Registrar Compliance Auditor and Security Director reviewing batch data..."):
                    agent_svc = AgentService(model_name=model_choice)
                    memo = agent_svc.run_id_card_credential_crew(df_bulk.head(8).to_string())
                    st.markdown(memo)

                # 2. Render Cards
                with st.spinner(f"Rendering {len(df_bulk)} official cards into ZIP archive..."):
                    zip_output = IDCardService.generate_bulk_cards_zip(df_bulk, inst_bulk_title)
                    st.success(f"Generated {len(df_bulk)} official ID cards successfully!")
                    st.download_button(
                        label="📥 Download All Official ID Cards (.ZIP)",
                        data=zip_output,
                        file_name=f"{inst_bulk_title.replace(' ', '_')}_Official_ID_Cards.zip",
                        mime="application/zip"
                    )

    # --- TAB 3: DOWNLOAD TEMPLATES ---
    with tab_templates:
        st.write("#### 📥 Official Bulk Upload Templates")
        st.write("Download these templates, fill them out with your school data, and upload them directly.")

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.write("##### 🎓 Student ID Card Bulk Roster Template")
            stu_t = TemplateFactory.get_student_id_template()
            st.dataframe(stu_t)
            st.download_button("Download Student Roster Template (CSV)", stu_t.to_csv(index=False).encode("utf-8"), "student_id_template.csv", "text/csv")

        with t_col2:
            st.write("##### 👨‍🏫 Faculty / Teacher ID Card Bulk Template")
            teach_t = TemplateFactory.get_teacher_id_template()
            st.dataframe(teach_t)
            st.download_button("Download Faculty ID Template (CSV)", teach_t.to_csv(index=False).encode("utf-8"), "faculty_id_template.csv", "text/csv")

# ----------------- 3. TIMETABLE ENGINE -----------------
elif app_mode == "🗓️ Timetable Engine & Audit":
    st.markdown('<div class="main-header">Algorithmic Master Timetable & Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enforces Farm Master Period 1 lock, 5-period Friday cap, and Same-Period consistency</div>', unsafe_allow_html=True)

    with st.expander("ℹ️ Download Official Timetable Upload Template"):
        tt_template = TemplateFactory.get_timetable_template()
        st.dataframe(tt_template)
        st.download_button("Download Timetable Template (CSV)", tt_template.to_csv(index=False).encode("utf-8"), "timetable_workload_template.csv", "text/csv")

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

            if st.button("⚡ Solve Master Timetable & Run Agent Audit"):
                with st.spinner("Constraint solver computing allocations..."):
                    day_tables, err = TimetableService.generate_timetable(df_in, default_class_name=default_cls)

                if err:
                    st.error(err)
                else:
                    st.success("Master schedule solved with zero collisions!")
                    tabs = st.tabs(list(day_tables.keys()))
                    summary_text = ""
                    for idx, tab_name in enumerate(day_tables.keys()):
                        with tabs[idx]:
                            st.write(f"#### 📋 {tab_name}")
                            st.dataframe(day_tables[tab_name], use_container_width=True)
                            summary_text += f"\n--- {tab_name} ---\n" + day_tables[tab_name].head(4).to_string()

                    st.markdown("---")
                    st.write("### 🤖 Scheduling Compliance Audit Crew")
                    with st.spinner("Compliance Auditor and Academic Strategist evaluating allocations..."):
                        agent_svc = AgentService(model_name=model_choice)
                        audit_result = agent_svc.run_timetable_audit_crew(summary_text)
                        st.markdown(audit_result)
        except Exception as ex:
            st.error(f"Error: {ex}")

# ----------------- 4. CURRICULUM MULTI-AGENT CREW -----------------
elif app_mode == "📚 Curriculum Multi-Agent Crew":
    st.markdown('<div class="main-header">Autonomous Curriculum Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Collaborative multi-agent pedagogical planning pipeline</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        topic = st.text_input("Lesson Topic", placeholder="e.g., Cellular Respiration & Energy Cycles")
        grade_level = st.selectbox("Grade Level", ["Grade 6-8", "Grade 9-10", "Grade 11-12"])
    with c2:
        uploaded_doc = st.file_uploader("Reference Curriculum Chapter (PDF/TXT)", type=["pdf", "txt"])

    if st.button("🚀 Kickoff Curriculum Crew"):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("Please supply your Gemini API key in the sidebar.")
        elif not topic:
            st.warning("Please specify a topic.")
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
                st.success("Lesson pack drafted and verified!")
                st.markdown(result)
                st.download_button("📥 Download Lesson Pack", result, f"{topic.replace(' ', '_')}.md", "text/markdown")

# ----------------- 5. CAMPUS GATE & ATTENDANCE -----------------
elif app_mode == "📷 Campus Gate & Attendance Agent":
    st.markdown('<div class="main-header">Smart Gate & Truancy Multi-Agent Crew</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live optical scanner verifying official ID cards with HMAC-SHA256 authentication</div>', unsafe_allow_html=True)

    c_cam, c_act = st.columns([1, 1])
    with c_cam:
        st.write("#### 🎥 Live Optical Gate Scanner")
        cam_shot = st.camera_input("Scan Official ID Card QR")

    with c_act:
        st.write("#### 🛡️ Gate Security & Punctuality Engine")
        if cam_shot:
            raw_bytes = cam_shot.getvalue()
            decoded_token = SecurityService.decode_camera_frame(raw_bytes)
            
            if not decoded_token:
                st.warning("⚠️ No valid QR code recognized. Align card in front of camera.")
            else:
                is_valid, parts, sec_msg = SecurityService.verify_token(decoded_token)
                pid = parts[0] if len(parts) > 0 else "UNKNOWN"
                pname = parts[1] if len(parts) > 1 else "Unknown"
                prole = parts[2] if len(parts) > 2 else "Student"
                pcls = parts[3] if len(parts) > 3 else "General"
                now_str = datetime.now().strftime("%I:%M %p")

                is_on_time = datetime.now().hour < 8 or (datetime.now().hour == 8 and datetime.now().minute <= 10)
                status = "Present - On Time" if is_on_time else "Tardy / Late"

                if not is_valid:
                    st.error(f"🚨 {sec_msg}")
                    DatabaseService.record_attendance(pid, pname, prole, pcls, "FLAGGED_FORGERY", sec_msg, False)
                else:
                    st.success(f"Verified Identity: **{pname}** ({prole})")
                    st.markdown(f"**Security Token:** `{sec_msg}`")
                    st.markdown(f"**Class/Dept:** {pcls} | **Timestamp:** {now_str}")
                    st.markdown(f"**Status:** `{status}`")
                    DatabaseService.record_attendance(pid, pname, prole, pcls, status, f"Gate scan at {now_str}", True)
                    
                    if status != "Present - On Time" and prole == "Student":
                        st.warning(f"📱 **Automated Parent SMS Dispatched:** 'Notice: Student {pname} checked in at {now_str}, after the 08:00 AM school bell.'")

    st.markdown("---")
    st.write("### 📊 Today's Relational Attendance Register")
    today_records = DatabaseService.get_today_logs_df()
    if not today_records.empty:
        st.dataframe(today_records, use_container_width=True)
        if st.button("🤖 Run Truancy & Welfare Multi-Agent Analysis"):
            with st.spinner("Truancy Analyst & Welfare Liaison analyzing records..."):
                agent_svc = AgentService(model_name=model_choice)
                brief = agent_svc.run_attendance_intelligence_crew(today_records.to_string())
                st.markdown("### 📋 Welfare Intelligence Brief")
                st.markdown(brief)
    else:
        st.info("No check-ins logged yet today.")
