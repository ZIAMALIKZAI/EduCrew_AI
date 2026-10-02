import os
import streamlit as st
import pandas as pd
from pathlib import Path

from core.config import UPLOADS_DIR
from ui.styles import apply_custom_styles
from services.agent_service import AgentService
from services.document_service import DocumentService
from services.timetable_service import TimetableService

st.set_page_config(page_title="EduCrew AI - Autonomous School Assistant", page_icon="🎓", layout="wide")
apply_custom_styles()

with st.sidebar:
    st.title("⚙️ EduCrew Settings")
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=env_api_key, type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    model_choice = st.selectbox("Gemini Engine", options=["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    st.markdown("---")
    app_mode = st.radio("Select Capability", ["Multi-Agent Lesson & Quiz Architect", "Automated Timetable Generator"])

st.markdown('<div class="main-header">🎓 EduCrew AI: Multi-Agent Teacher Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Collaborative Generative Agents for Pedagogical Planning and School Scheduling</div>', unsafe_allow_html=True)

# ----------------- MODULE 1: MULTI-AGENT LESSON ARCHITECT -----------------
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

# ----------------- MODULE 2: TIMETABLE GENERATOR -----------------
elif app_mode == "Automated Timetable Generator":
    st.subheader("📅 School Timetable Generator (Same-Period Consistency & Multi-Class)")
    st.write(
        "Upload a roster file (CSV/Excel). The algorithm guarantees:\n"
        "- **Consistent Timing:** If a teacher has multiple periods with a class, they take place at the **same period/time** on different days.\n"
        "- **Max 1 Period/Day:** Teachers do not take more than one period with the same class on the same day.\n"
        "- **Farm Master Priority:** Period 1 is reserved for the Farm Master from Monday to Saturday.\n"
        "- **Friday Short Day:** Exactly 5 periods on Friday; 8 periods on other days."
    )

    template_df = pd.DataFrame({
        "Teacher Name": [
            "Mr. Ahmad Khan",
            "Ms. Fatima Noor",
            "Mr. Tariq Mehmood",
            "Ms. Ayesha Bibi",
            "Mr. Tariq Mehmood"
        ],
        "Designation": [
            "Farm Master",
            "Senior Subject Specialist",
            "Subject Specialist",
            "Junior Teacher",
            "Subject Specialist"
        ],
        "Class": [
            "Class 10th",
            "Class 10th",
            "Class 10th",
            "Class 10th",
            "Class 9th"
        ],
        "Periods Per Week": [6, 4, 3, 4, 3],
        "Subject": [
            "Agriculture & Biology",
            "Physics",
            "Mathematics",
            "English",
            "Mathematics"
        ]
    })

    with st.expander("ℹ️ Expected File Format (Preview & Download Sample)"):
        st.dataframe(template_df)
        csv_sample = template_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Sample CSV", csv_sample, "sample_teachers.csv", "text/csv")

    timetable_file = st.file_uploader("Upload Teachers Data File", type=["csv", "xlsx", "xls"])

    if timetable_file:
        saved_tt_path = UPLOADS_DIR / timetable_file.name
        with open(saved_tt_path, "wb") as f:
            f.write(timetable_file.getbuffer())

        try:
            df_in = DocumentService.read_tabular(saved_tt_path)
            st.write("Loaded Data Preview:")
            st.dataframe(df_in.head(8))

            if st.button("⚡ Generate Weekly Timetable"):
                with st.spinner("Generating timetable based on constraints..."):
                    day_tables, err = TimetableService.generate_timetable(df_in)
                    if err:
                        st.error(err)
                    else:
                        st.success("Timetable generated successfully!")
                        tabs = st.tabs(list(day_tables.keys()))
                        for idx, sheet_name in enumerate(day_tables.keys()):
                            with tabs[idx]:
                                st.write(f"### Schedule: {sheet_name}")
                                st.dataframe(day_tables[sheet_name], use_container_width=True)

                        output_excel = UPLOADS_DIR / "Generated_Weekly_Timetable.xlsx"
                        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                            for sheet_name, ddf in day_tables.items():
                                # Excel sheet name limit is 31 characters
                                safe_name = sheet_name[:31]
                                ddf.to_excel(writer, sheet_name=safe_name, index=False)

                        with open(output_excel, "rb") as f:
                            st.download_button(
                                label="📥 Download Complete Timetable (Excel)",
                                data=f.read(),
                                file_name="Weekly_Timetable.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        except Exception as ex:
            st.error(f"Error parsing file: {ex}")
