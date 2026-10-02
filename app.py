import os
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from core.config import UPLOADS_DIR
from ui.styles import apply_custom_styles
from services.agent_service import AgentService
from services.document_service import DocumentService
from services.timetable_service import TimetableService
from services.attendance_service import AttendanceService

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

    model_choice = st.selectbox(
        "Gemini Engine",
        options=["gemini-1.5-flash", "gemini-1.5-pro"],
        index=0
    )

    st.markdown("---")
    app_mode = st.radio(
        "Select Capability",
        [
            "Multi-Agent Lesson & Quiz Architect",
            "Automated Timetable Generator",
            "Live QR Attendance & Agent Monitor"
        ]
    )

st.markdown('<div class="main-header">🎓 EduCrew AI: Multi-Agent Teacher Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Collaborative Generative Agents for Lesson Design, Timetables, and Attendance</div>', unsafe_allow_html=True)

# 1. LESSON ARCHITECT
if app_mode == "Multi-Agent Lesson & Quiz Architect":
    st.subheader("🤖 Multi-Agent Curriculum & Assessment Team")
    st.write("Specialized agents design your lesson plan, formulate assessments, and differentiate for different learner needs.")

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

# 2. TIMETABLE GENERATOR
elif app_mode == "Automated Timetable Generator":
    st.subheader("📅 School Timetable Generator (With Class Names & Same-Period Timing)")
    st.write(
        "Upload a CSV/Excel file with teacher details. The engine guarantees:\n"
        "- **Class Name Displayed**: Every schedule clearly states the Class in the first column.\n"
        "- **Consistent Slot Timing**: A teacher teaching the same class multiple days takes the **same period/time**.\n"
        "- **Farm Master Lock**: Period 1 on Monday to Saturday is reserved for the Farm Master.\n"
        "- **Friday Constraint**: Exactly 5 periods on Friday; 8 periods on other days."
    )

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

# 3. QR ATTENDANCE SCANNER
elif app_mode == "Live QR Attendance & Agent Monitor":
    st.subheader("📷 Live QR Attendance & Agent Verification")
    st.write("Point an ID card QR code at the camera. The AI Attendance Agent parses the person, checks punctuality against the 8:00 AM bell, and logs the entry.")

    with st.expander("🛠️ Generate Test QR Codes (Print or Scan from Phone Screen)"):
        st.write("Copy or display any of these sample text strings in any QR generator (format: `ID|Name|Role|Class`):")
        st.code("T101|Mr. Ahmad Khan|Teacher - Farm Master|Class 10th", language="text")
        st.code("S502|Zia Malik|Student|Class 10th-A", language="text")
        st.code("S503|Ayesha Noor|Student|Class 9th-B", language="text")

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
