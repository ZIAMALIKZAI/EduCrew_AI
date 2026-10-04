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
from services.pdf_service import PDFReportService

DatabaseService.init_database()

# ----------------- PAKISTANI SCHOOL CLASSES & DESIGNATIONS -----------------
PAK_CLASSES = [
    "Nursery", "Prep / K.G",
    "Class 1st", "Class 2nd", "Class 3rd", "Class 4th", "Class 5th (Primary)",
    "Class 6th", "Class 7th", "Class 8th (Middle)",
    "Class 9th", "Class 10th (Matric)",
    "Class 11th (1st Year)", "Class 12th (2nd Year)"
]

PAK_DESIGNATIONS = [
    ("Primary School Teacher (PST)", "14", "Primary Section"),
    ("Elementary School Teacher (EST)", "15", "Middle Section"),
    ("Secondary School Teacher (SST)", "16", "High School Section"),
    ("Senior Subject Specialist (SS)", "17", "Higher Secondary"),
    ("Farm Master / Agriculture Specialist", "16", "Vocational & Agriculture"),
    ("Physical Training Instructor (PTI)", "15", "Sports & Health"),
    ("Drawing Master (DM)", "15", "Fine Arts"),
    ("Arabic / Qari Teacher (AT)", "15", "Islamic Studies"),
    ("Principal / Headmaster", "19", "Administration"),
    ("Vice Principal", "18", "Administration")
]

# ----------------- UNIVERSAL TEMPLATES GENERATOR -----------------
class TemplateFactory:
    @staticmethod
    def get_timetable_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Class": ["Class 10th", "Class 10th", "Class 9th", "Class 9th", "Class 5th", "Class 5th"],
            "Teacher Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood", "Ms. Ayesha Bibi", "Mr. Asad Ullah", "Mr. Rashid Minhas"],
            "Designation": ["Farm Master", "Senior Subject Specialist", "Secondary School Teacher", "Elementary School Teacher", "Primary School Teacher", "Physical Training Instructor"],
            "Periods Per Week": [6, 4, 4, 4, 5, 3],
            "Subject": ["Agriculture", "Physics", "Mathematics", "English", "General Science", "Physical Education"]
        })

    @staticmethod
    def get_student_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Admission No": ["ADM-2026-01", "ADM-2026-02", "ADM-2026-03", "ADM-2026-04", "ADM-2026-05"],
            "Class Roll No": [1, 2, 14, 5, 21],
            "Student Name": ["Muhammad Huzaifa", "Fatima Bibi", "Ali Ahmad", "Ayesha Noor", "Zayan Malik"],
            "Father Name": ["Tariq Mehmood", "Noor Muhammad", "Ahmad Hassan", "Zahid Khan", "Muhammad Asif"],
            "Class": ["Nursery", "Class 2nd", "Class 5th (Primary)", "Class 9th", "Class 10th (Matric)"],
            "Section": ["A", "A", "B", "A", "B"],
            "Blood Group": ["B+", "O+", "A+", "AB+", "O-"],
            "Emergency Contact": ["0301-1234567", "0312-9876543", "0333-5554433", "0345-7778899", "0300-1122334"]
        })

    @staticmethod
    def get_staff_template() -> pd.DataFrame:
        return pd.DataFrame({
            "Personal No": ["P-984321", "P-874512", "P-651234", "P-542198"],
            "Staff Name": ["Mr. Ahmad Khan", "Ms. Fatima Noor", "Mr. Tariq Mehmood", "Mr. Bilal Akhtar"],
            "Designation": ["Farm Master", "Senior Subject Specialist", "Secondary School Teacher", "Primary School Teacher"],
            "BPS Scale": ["16", "17", "16", "14"],
            "Department": ["Agriculture", "Physics Dept", "Mathematics", "Primary Wing"],
            "CNIC": ["17301-1234567-1", "17301-7654321-2", "17301-9988776-3", "17301-4455667-4"],
            "Official Email": ["ahmad.khan@school.edu.pk", "fatima.noor@school.edu.pk", "tariq.m@school.edu.pk", "bilal.a@school.edu.pk"],
            "Mobile Phone": ["0300-9876543", "0301-2345678", "0333-8765432", "0345-1234567"],
            "Emergency Contact": ["0302-1111111", "0303-2222222", "0304-3333333", "0305-4444444"],
            "Blood Group": ["O+", "A+", "B+", "B+"]
        })

# ----------------- SECURITY ENGINE -----------------
class SecurityService:
    @classmethod
    def verify_token(cls, full_token: str):
        if "#" not in full_token:
            return False, full_token.split("|"), "Unsigned QR Code (Non-Institutional / Invalid)"
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

# ----------------- STREAMLIT PORTAL SETUP -----------------
st.set_page_config(page_title="EduCrew AI | Pakistan School Operations", page_icon="🏫", layout="wide")
apply_custom_styles()

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# Sign-In Screen
if not st.session_state["auth_user"]:
    st.markdown('<div class="main-header" style="text-align:center;">🏛️ EduCrew Pakistan School Suite</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header" style="text-align:center;">Multi-Agent Education Management System (Primary, Middle, High & Higher Secondary)</div>', unsafe_allow_html=True)

    c_log, _ = st.columns([1, 1])
    with c_log:
        with st.form("login_box"):
            st.write("#### 🔐 Institutional Access Portal")
            u_name = st.text_input("Username", value="admin")
            u_pass = st.text_input("Password", type="password", value="admin123")
            btn = st.form_submit_button("Sign In")
            if btn:
                u = DatabaseService.authenticate_user(u_name, u_pass)
                if u:
                    st.session_state["auth_user"] = u
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.info("Logins:\n- **Principal**: `admin` / `admin123`\n- **Faculty**: `teacher` / `teach123`\n- **Gate Sentry**: `gate` / `gate123`")
    st.stop()

current_user = st.session_state["auth_user"]
user_role = current_user["role"]

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=54)
    st.markdown("### **EduCrew Pakistan**")
    st.caption(f"User: **{current_user['full_name']}** | Role: `{user_role}`")

    if st.button("🚪 Log Out"):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("---")
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=env_api_key, type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    # Updated to active 2.5 foundation models to resolve 404 NOT_FOUND
    model_choice = st.selectbox("Gemini Engine", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)
    st.markdown("---")

    if user_role == "Principal":
        nav = [
            "🏛️ Institutional Dashboard",
            "🪪 Student Official ID Card Studio",
            "👨‍🏫 Faculty & Staff Official Card Studio",
            "🗓️ Timetable Engine & Audit",
            "📚 Multi-Agent Lesson Architect",
            "📷 Campus Gate & Attendance Agent"
        ]
    elif user_role == "Teacher":
        nav = [
            "📚 Multi-Agent Lesson Architect",
            "🗓️ Timetable Engine & Audit",
            "🪪 Student Official ID Card Studio",
            "📷 Campus Gate & Attendance Agent"
        ]
    else:
        nav = ["📷 Campus Gate & Attendance Agent"]

    app_mode = st.radio("System Navigation", nav)

# ----------------- 1. INSTITUTIONAL DASHBOARD -----------------
if app_mode == "🏛️ Institutional Dashboard":
    st.markdown('<div class="main-header">Institutional Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Telemetry for Nursery through Class 12th & Faculty Cadres</div>', unsafe_allow_html=True)

    today_logs = DatabaseService.get_today_logs_df()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="kpi-card"><div class="kpi-value">Nursery to 12th</div><div class="kpi-label">Active Academic Classes</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(today_logs)}</div><div class="kpi-label">Today Scans</div></div>', unsafe_allow_html=True)
    with c3:
        forged = len(today_logs[today_logs["Authenticated"] == 0]) if not today_logs.empty else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:#DC2626;">{forged}</div><div class="kpi-label">Tamper Flags</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="kpi-card"><div class="kpi-value">Locked P-1</div><div class="kpi-label">Farm Master Mon-Sat</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("### 🗄 Relational Database Check-In Ledger")
    if not today_logs.empty:
        st.dataframe(today_logs, use_container_width=True)
    else:
        st.info("No scans recorded yet today.")

# ----------------- 2. STUDENT ID CARD STUDIO (NURSERY TO 12TH) -----------------
elif app_mode == "🪪 Student Official ID Card Studio":
    st.markdown('<div class="main-header">Student Official ID Card Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generates verified student identity cards with Father Name, Roll No, Class, Emergency Contact & School Phone/Email</div>', unsafe_allow_html=True)

    tab_s_single, tab_s_bulk, tab_s_template = st.tabs(["👤 Single Student Card", "📁 Bulk Students (CSV/Excel) to ZIP", "📥 Download Student Template"])

    with tab_s_single:
        st.write("#### Issue Student ID Card")
        s1, s2, s3 = st.columns(3)
        with s1:
            inst_name = st.text_input("School Name Header", "GOVERNMENT HIGH SCHOOL YAR HUSSAIN")
            stu_name = st.text_input("Student Name", "Muhammad Huzaifa")
            f_name = st.text_input("Father's Name", "Tariq Mehmood")
        with s2:
            c_choice = st.selectbox("Class Level", PAK_CLASSES, index=6)
            sec_choice = st.selectbox("Section", ["A", "B", "C", "D"], index=0)
            roll_no = st.number_input("Class Roll Number", min_value=1, max_value=200, value=12)
            adm_no = st.text_input("Admission / Reg No", "ADM-2026-44")
        with s3:
            b_group = st.selectbox("Blood Group", ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"])
            emg_phone = st.text_input("Parent / Emergency Mobile", "0300-1234567")
            sch_phone = st.text_input("School Official Phone", "+92 938 123456")
            sch_mail = st.text_input("School Official Email", "ghs.yarhussain@kp.gov.pk")

        if st.button("🪪 Render Student ID Card"):
            card = IDCardService.create_student_card(
                admission_no=adm_no,
                roll_no=str(roll_no),
                student_name=stu_name,
                father_name=f_name,
                class_name=c_choice,
                section=sec_choice,
                blood_group=b_group,
                emergency_contact=emg_phone,
                school_name=inst_name,
                school_phone=sch_phone,
                school_email=sch_mail
            )
            b = io.BytesIO()
            card.save(b, format="PNG")
            c_img, c_info = st.columns([1, 1])
            with c_img:
                st.image(b.getvalue(), width=320)
            with c_info:
                st.success("Student Card Rendered Successfully")
                st.write(f"**Student:** {stu_name} s/o {f_name}")
                st.write(f"**Class:** {c_choice} ({sec_choice}) | **Roll No:** {roll_no}")
                st.write(f"**School Phone:** {sch_phone} | **Email:** {sch_mail}")
                st.download_button("📥 Download Card (PNG)", b.getvalue(), f"{c_choice}_{roll_no}_{stu_name}.png", "image/png")

    with tab_s_bulk:
        st.write("#### Bulk Student Card Generation")
        b_school = st.text_input("Bulk School Header", "GOVERNMENT HIGH SCHOOL YAR HUSSAIN")
        b_sch_phone = st.text_input("School Telephone", "+92 938 123456", key="b_s_phone")
        b_sch_email = st.text_input("School Email", "ghs.yarhussain@kp.gov.pk", key="b_s_mail")
        stu_file = st.file_uploader("Upload Student Roster (CSV / Excel)", type=["csv", "xlsx"])

        if stu_file:
            df_stu = pd.read_csv(stu_file) if stu_file.name.endswith(".csv") else pd.read_excel(stu_file)
            st.dataframe(df_stu.head(5), use_container_width=True)

            if st.button("⚡ Run Agent & Build All Student Cards (.ZIP)"):
                with st.spinner("Registrar Credential Agent inspecting student records..."):
                    agent_svc = AgentService(model_name=model_choice)
                    memo = agent_svc.run_id_card_credential_crew(df_stu.head(6).to_string())
                    st.markdown("### 📋 Credential Audit Memo")
                    st.markdown(memo)

                with st.spinner("Rendering batch student cards into ZIP archive..."):
                    z_bytes = IDCardService.generate_bulk_student_cards_zip(df_stu, b_school, b_sch_phone, b_sch_email)
                    st.success(f"Built {len(df_stu)} student cards successfully!")
                    st.download_button("📥 Download Student Cards (.ZIP)", z_bytes, "Student_ID_Cards.zip", "application/zip")

    with tab_s_template:
        st.write("#### Download Official Student Bulk Roster Template")
        s_tmpl = TemplateFactory.get_student_template()
        st.dataframe(s_tmpl)
        st.download_button("📥 Download Student Roster Template (CSV)", s_tmpl.to_csv(index=False).encode("utf-8"), "student_roster_template.csv", "text/csv")

# ----------------- 3. FACULTY & STAFF ID CARD STUDIO -----------------
elif app_mode == "👨‍🏫 Faculty & Staff Official Card Studio":
    st.markdown('<div class="main-header">Faculty & Staff Official ID Card Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pakistani educational designations (PST, EST, SST, Farm Master, SS, Principal) with BPS Scale, CNIC, and Official Email</div>', unsafe_allow_html=True)

    tab_t_single, tab_t_bulk, tab_t_template = st.tabs(["👨‍🏫 Single Faculty Card", "📁 Bulk Faculty (CSV/Excel) to ZIP", "📥 Download Faculty Template"])

    with tab_t_single:
        st.write("#### Issue Faculty / Staff Identity Card")
        t1, t2, t3 = st.columns(3)
        with t1:
            t_school = st.text_input("Institution Header", "GOVERNMENT HIGH SCHOOL YAR HUSSAIN", key="t_inst")
            t_name = st.text_input("Official Name", "Mr. Ahmad Khan")
            p_no = st.text_input("Personal / Employee No", "P-984210")
        with t2:
            desig_tuple = st.selectbox("Designation & BPS Grade", PAK_DESIGNATIONS, format_func=lambda x: f"{x[0]} (BPS-{x[1]})")
            dept_name = st.text_input("Department / Wing", desig_tuple[2])
            cnic = st.text_input("CNIC Number", "17301-7654321-3")
        with t3:
            t_email = st.text_input("Official Staff Email", "ahmad.khan@school.edu.pk")
            t_phone = st.text_input("Official Mobile Phone", "0300-1234567")
            t_emg = st.text_input("Emergency Contact", "0301-9876543")
            t_blood = st.selectbox("Blood Group", ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"], key="t_bld")

        if st.button("🪪 Render Faculty Official Card"):
            card_t = IDCardService.create_staff_card(
                emp_id=p_no,
                staff_name=t_name,
                designation=desig_tuple[0],
                bps_scale=desig_tuple[1],
                department=dept_name,
                cnic_no=cnic,
                official_email=t_email,
                mobile_no=t_phone,
                emergency_contact=t_emg,
                blood_group=t_blood,
                institution_name=t_school,
                school_phone="+92 938 123456"
            )
            b_t = io.BytesIO()
            card_t.save(b_t, format="PNG")
            c_t_img, c_t_info = st.columns([1, 1])
            with c_t_img:
                st.image(b_t.getvalue(), width=320)
            with c_t_info:
                st.success("Faculty Card Rendered Successfully")
                st.write(f"**Name:** {t_name} | **Designation:** {desig_tuple[0]} (BPS-{desig_tuple[1]})")
                st.write(f"**CNIC:** {cnic} | **Personal No:** {p_no}")
                st.write(f"**Official Email:** {t_email}")
                st.download_button("📥 Download Card (PNG)", b_t.getvalue(), f"{t_name.replace(' ', '_')}_StaffCard.png", "image/png")

    with tab_t_bulk:
        st.write("#### Bulk Faculty Card Production")
        b_t_school = st.text_input("Bulk Institution Header", "GOVERNMENT HIGH SCHOOL YAR HUSSAIN", key="b_t_inst")
        staff_file = st.file_uploader("Upload Staff Roster (CSV / Excel)", type=["csv", "xlsx"])

        if staff_file:
            df_stf = pd.read_csv(staff_file) if staff_file.name.endswith(".csv") else pd.read_excel(staff_file)
            st.dataframe(df_stf.head(5), use_container_width=True)

            if st.button("⚡ Run Credential Agent & Build Staff Cards (.ZIP)"):
                with st.spinner("Registrar Identity Auditor verifying staff records..."):
                    agent_svc = AgentService(model_name=model_choice)
                    memo = agent_svc.run_id_card_credential_crew(df_stf.head(5).to_string())
                    st.markdown("### 📋 Credential Audit Memo")
                    st.markdown(memo)

                with st.spinner("Rendering batch staff cards into ZIP archive..."):
                    z_stf = IDCardService.generate_bulk_staff_cards_zip(df_stf, b_t_school, "+92 938 123456")
                    st.success(f"Built {len(df_stf)} faculty cards successfully!")
                    st.download_button("📥 Download Staff Cards (.ZIP)", z_stf, "Faculty_ID_Cards.zip", "application/zip")

    with tab_t_template:
        st.write("#### Download Official Faculty / Staff Bulk Template")
        f_tmpl = TemplateFactory.get_staff_template()
        st.dataframe(f_tmpl)
        st.download_button("📥 Download Faculty Template (CSV)", f_tmpl.to_csv(index=False).encode("utf-8"), "faculty_roster_template.csv", "text/csv")

# ----------------- 4. TIMETABLE ENGINE & AUDIT -----------------
elif app_mode == "🗓️ Timetable Engine & Audit":
    st.markdown('<div class="main-header">Algorithmic Timetable Engine & Multi-Agent Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Supports Primary to Higher Secondary. Enforces Farm Master Period 1, Friday 5-period rule, and same-period slot consistency.</div>', unsafe_allow_html=True)

    with st.expander("ℹ️ Download Official Timetable Template"):
        tt_tmpl = TemplateFactory.get_timetable_template()
        st.dataframe(tt_tmpl)
        st.download_button("📥 Download Timetable Template (CSV)", tt_tmpl.to_csv(index=False).encode("utf-8"), "timetable_template.csv", "text/csv")

    col_up, col_name = st.columns([2, 1])
    with col_up:
        tt_file = st.file_uploader("Upload Faculty Workload Spreadsheet", type=["csv", "xlsx", "xls"])
    with col_name:
        default_cls = st.selectbox("Default Class (if not in file)", PAK_CLASSES, index=6)

    if tt_file:
        saved_path = UPLOADS_DIR / tt_file.name
        with open(saved_path, "wb") as f:
            f.write(tt_file.getbuffer())

        try:
            df_in = DocumentService.read_tabular(saved_path)
            st.dataframe(df_in.head(6), use_container_width=True)

            if st.button("⚡ Solve Timetable & Run Agent Audit"):
                with st.spinner("Constraint solver generating schedule..."):
                    day_tables, err = TimetableService.generate_timetable(df_in, default_class_name=default_cls)

                if err:
                    st.error(err)
                else:
                    st.success("Master schedule solved with zero clashes!")
                    tabs = st.tabs(list(day_tables.keys()))
                    summary_text = ""
                    for idx, tab_name in enumerate(day_tables.keys()):
                        with tabs[idx]:
                            st.write(f"#### 📋 {tab_name}")
                            st.dataframe(day_tables[tab_name], use_container_width=True)
                            summary_text += f"\n--- {tab_name} ---\n" + day_tables[tab_name].head(4).to_string()

                    st.markdown("---")
                    st.write("### 🤖 Scheduling Compliance Audit Crew")
                    with st.spinner("Registrar Auditor and Operations Strategist analyzing allocations..."):
                        agent_svc = AgentService(model_name=model_choice)
                        audit_result = agent_svc.run_timetable_audit_crew(summary_text)
                        st.markdown(audit_result)
        except Exception as ex:
            st.error(f"Error: {ex}")

# ----------------- 5. CURRICULUM MULTI-AGENT CREW -----------------
elif app_mode == "📚 Multi-Agent Lesson Architect":
    st.markdown('<div class="main-header">Autonomous Curriculum Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Collaborative multi-agent pedagogical design with direct PDF and Markdown export</div>', unsafe_allow_html=True)

    # Initialize session state keys for reliable re-rendering
    if "current_lesson_result" not in st.session_state:
        st.session_state["current_lesson_result"] = None
    if "current_lesson_pdf" not in st.session_state:
        st.session_state["current_lesson_pdf"] = None
    if "current_lesson_topic" not in st.session_state:
        st.session_state["current_lesson_topic"] = ""
    if "current_lesson_grade" not in st.session_state:
        st.session_state["current_lesson_grade"] = ""

    c1, c2 = st.columns([1, 1])
    with c1:
        topic = st.text_input("Lesson Topic", placeholder="e.g., Photosynthesis & Plant Physiology")
        grade_level = st.selectbox("Grade Level", PAK_CLASSES, index=6)
    with c2:
        uploaded_doc = st.file_uploader(
            "Optional: Reference Book Chapter (PDF, TXT, or Photo: JPG, PNG)",
            type=["pdf", "txt", "jpg", "jpeg", "png", "webp"]
        )

    if st.button("🚀 Kickoff Curriculum Crew"):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("Please supply your Gemini API key in the sidebar.")
        elif not topic:
            st.warning("Please specify a topic.")
        else:
            with st.spinner("Curriculum Designer, Assessment Specialist, Inclusion Coach, Lab Specialist, and Board Architect collaborating..."):
                doc_text = ""
                if uploaded_doc:
                    saved_path = UPLOADS_DIR / uploaded_doc.name
                    with open(saved_path, "wb") as f:
                        f.write(uploaded_doc.getbuffer())
                    doc_text = DocumentService.extract_text(saved_path)

                agent_svc = AgentService(model_name=model_choice)
                result = agent_svc.run_lesson_planning_workflow(topic, grade_level, doc_text)

                pdf_bytes = PDFReportService.generate_lesson_pdf(
                    topic=topic,
                    grade_level=grade_level,
                    markdown_content=result,
                    school_name="GOVERNMENT HIGH SCHOOL"
                )

                st.session_state["current_lesson_result"] = result
                st.session_state["current_lesson_pdf"] = pdf_bytes
                st.session_state["current_lesson_topic"] = topic
                st.session_state["current_lesson_grade"] = grade_level

    # Render results and persistent download buttons if present in state
    if st.session_state.get("current_lesson_result"):
        st.success("Lesson pack drafted and verified by all autonomous agents!")
        st.markdown(st.session_state["current_lesson_result"])

        st.markdown("---")
        st.write("### 📥 Download Institutional Deliverables")
        col_pdf, col_md = st.columns(2)

        safe_topic = str(st.session_state.get("current_lesson_topic", "Lesson")).replace(' ', '_')
        safe_grade = str(st.session_state.get("current_lesson_grade", "General")).replace(' ', '_').replace('/', '_')

        if st.session_state.get("current_lesson_pdf"):
            with col_pdf:
                st.download_button(
                    label="📄 Download Official Printable Lesson Pack (PDF)",
                    data=st.session_state["current_lesson_pdf"],
                    file_name=f"{safe_topic}_{safe_grade}_Lesson_Pack.pdf",
                    mime="application/pdf"
                )

        with col_md:
            st.download_button(
                label="📝 Download Editable Source (Markdown)",
                data=st.session_state["current_lesson_result"],
                file_name=f"{safe_topic}.md",
                mime="text/markdown"
            )

# ----------------- 6. CAMPUS GATE SCANNER & ATTENDANCE -----------------
elif app_mode == "📷 Campus Gate & Attendance Agent":
    st.markdown('<div class="main-header">Smart Campus Gate & Truancy Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Optical live scanner recognizing both Student Cards & Faculty Cards with automated gate rules</div>', unsafe_allow_html=True)

    c_cam, c_act = st.columns([1, 1])
    with c_cam:
        st.write("#### 🎥 Live Optical Gate Scanner")
        cam_shot = st.camera_input("Scan Student / Faculty ID Card")

    with c_act:
        st.write("#### 🛡️ Gate Verification & Punctuality Engine")
        if cam_shot:
            raw_bytes = cam_shot.getvalue()
            decoded_token = SecurityService.decode_camera_frame(raw_bytes)

            if not decoded_token:
                st.warning("⚠️ No valid QR code recognized. Align card in front of camera.")
            else:
                is_valid, parts, sec_msg = SecurityService.verify_token(decoded_token)
                now_str = datetime.now().strftime("%I:%M %p")
                is_on_time = datetime.now().hour < 8 or (datetime.now().hour == 8 and datetime.now().minute <= 10)
                status = "Present - On Time" if is_on_time else "Tardy / Late"

                if not is_valid:
                    st.error(f"🚨 {sec_msg}")
                    DatabaseService.record_attendance("UNKNOWN", "Unverified Person", "Unknown", "General", "FLAGGED_FORGERY", sec_msg, False)
                else:
                    entity_type = parts[0]
                    if entity_type == "STU":
                        # Student Token: STU|AdmissionNo|Name|Class|RollNo|Emergency
                        adm_no, s_name, c_name, r_no, emg = parts[1], parts[2], parts[3], parts[4], parts[5]
                        st.success(f"Verified Student: **{s_name}**")
                        st.markdown(f"**Class:** {c_name} (Roll: {r_no}) | **Admission:** {adm_no}")
                        st.markdown(f"**Gate Time:** {now_str} | **Status:** `{status}`")
                        DatabaseService.record_attendance(adm_no, s_name, f"Student ({c_name})", c_name, status, f"Gate scan at {now_str}", True)
                        if status != "Present - On Time":
                            st.warning(f"📱 **Parent SMS Dispatched to {emg}:** 'Notice: Student {s_name} (Class {c_name}, Roll {r_no}) checked in at {now_str}, after the 08:00 AM bell.'")

                    elif entity_type == "STAFF":
                        # Staff Token: STAFF|EmpID|Name|Designation|Department|Mobile
                        e_id, t_name, desig, dept, phone = parts[1], parts[2], parts[3], parts[4], parts[5]
                        st.success(f"Verified Faculty: **{t_name}** ({desig})")
                        st.markdown(f"**Department:** {dept} | **Emp ID:** {e_id}")
                        st.markdown(f"**Gate Time:** {now_str} | **Status:** `{status}`")
                        DatabaseService.record_attendance(e_id, t_name, f"Faculty ({desig})", dept, status, f"Faculty check-in at {now_str}", True)

    st.markdown("---")
    st.write("### 📊 Today's Attendance Register")
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
