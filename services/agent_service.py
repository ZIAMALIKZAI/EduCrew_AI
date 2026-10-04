from crewai import Agent, Crew, Task, Process
from core.gemini import get_llm

class AgentService:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.llm = get_llm(model_name=model_name)

    # ---------------- 1. UPGRADED 5-AGENT ACADEMIC CURRICULUM CREW ----------------
    def run_lesson_planning_workflow(self, topic: str, grade_level: str, context_text: str = "") -> str:
        try:
            # 1. Lead Curriculum Architect
            designer = Agent(
                role="Lead Curriculum Architect",
                goal=f"Design an SLO-based 45-minute structured instructional timeline for {topic} ({grade_level}).",
                backstory=(
                    "Veteran instructional designer adhering strictly to national curriculum standards. "
                    "You excel at breaking complex subjects into structured, timed periods: "
                    "Warm-up, Direct Instruction, Guided Practice, and Summary Reflection."
                ),
                llm=self.llm,
                verbose=False
            )

            # 2. Bloom's Assessment Specialist
            evaluator = Agent(
                role="Senior Assessment Specialist",
                goal="Formulate Student Learning Objective (SLO) diagnostic quizzes and analytical rubrics.",
                backstory=(
                    "Provincial examination board specialist. You formulate 3 Multiple Choice Questions (MCQs), "
                    "2 conceptual short questions indexed to Bloom's Revised Taxonomy (Recall, Understanding, Application), "
                    "complete with an Answer Key and a 3-tier scoring rubric."
                ),
                llm=self.llm,
                verbose=False
            )

            # 3. Differentiated Education Coach
            inclusion = Agent(
                role="Differentiated Education Specialist",
                goal="Provide tiered interventions for remedial learners and extension tasks for advanced students.",
                backstory=(
                    "Inclusive education consultant. You understand mixed-ability classrooms and craft practical "
                    "remedial supports for struggling students without lowering standards, alongside challenging enrichment prompts."
                ),
                llm=self.llm,
                verbose=False
            )

            # 4. Activity & STEM Lab Specialist (NEW)
            lab_specialist = Agent(
                role="Activity & Practical Lab Specialist",
                goal="Design a low-cost, 10-minute hands-on activity or demonstration using everyday classroom items.",
                backstory=(
                    "Practical science and activity specialist who creates engaging, low-cost/no-cost "
                    "demonstrations that work even in schools with basic laboratory facilities."
                ),
                llm=self.llm,
                verbose=False
            )

            # 5. Bilingual Glossary & Blackboard Architect (NEW)
            board_architect = Agent(
                role="Bilingual Vocabulary & Blackboard Architect",
                goal="Build an English-Urdu technical vocabulary table and a clean blackboard diagram layout.",
                backstory=(
                    "Expert bilingual educator in Pakistan who bridges English terminology with Urdu explanations "
                    "and designs structured blackboard summaries (Left: Date/Objectives, Center: Diagrams/Notes, Right: Keywords)."
                ),
                llm=self.llm,
                verbose=False
            )

            # --- Define Tasks Sequentially ---
            t1 = Task(
                description=(
                    f"Design an SLO-aligned 45-minute lesson plan for '{topic}' target grade: '{grade_level}'.\n"
                    f"Reference material:\n{context_text[:1200] if context_text else 'Standard National Curriculum Scope'}\n"
                    "Structure:\n"
                    "- 3 Specific Student Learning Outcomes (SLOs)\n"
                    "- Period Timeline (0-5m Hook, 5-20m Direct Instruction, 20-35m Guided Practice, 35-45m Wrap-up)"
                ),
                expected_output="Detailed 45-minute lesson plan breakdown with explicit teacher and student actions.",
                agent=designer
            )

            t2 = Task(
                description=(
                    f"Using the lesson plan from Task 1 on '{topic}', develop:\n"
                    "1. 3 Multiple Choice Questions (with correct answer highlighted & explanation)\n"
                    "2. 2 Conceptual Short-Answer Questions\n"
                    "3. A 3-tier Assessment Rubric (Needs Support, Proficient, Advanced)"
                ),
                expected_output="Complete diagnostic quiz pack with answer keys and scoring rubric.",
                agent=evaluator
            )

            t3 = Task(
                description=(
                    f"Review the lesson and assessments for '{topic}'. Provide:\n"
                    "- 2 Remedial Classroom Accommodations (for slow readers / foundational learners)\n"
                    "- 2 Enrichment Challenges (for fast finishers / advanced students)"
                ),
                expected_output="Differentiated strategies table divided into Remedial Support and Enrichment Challenges.",
                agent=inclusion
            )

            t4 = Task(
                description=(
                    f"Develop a 10-minute active learning activity or low-cost science/STEM demonstration for '{topic}'.\n"
                    "Include:\n"
                    "- Title of Activity\n"
                    "- Required Materials (must be cheap/readily available)\n"
                    "- Step-by-step Execution\n"
                    "- Guiding Question to ask students during the activity"
                ),
                expected_output="Practical classroom activity or lab experiment plan.",
                agent=lab_specialist
            )

            t5 = Task(
                description=(
                    f"Finalize the lesson pack for '{topic}' ({grade_level}) with:\n"
                    "1. Bilingual Terminology Bank: 5 key scientific/academic terms with English spelling, Urdu translation, and brief meaning.\n"
                    "2. Blackboard Layout Blueprint: Text diagram showing how the teacher should partition the board (Left, Center, Right)."
                ),
                expected_output="Bilingual glossary table and ASCII/structured blackboard layout.",
                agent=board_architect
            )

            # Assemble the Sequential Crew
            crew = Crew(
                agents=[designer, evaluator, inclusion, lab_specialist, board_architect],
                tasks=[t1, t2, t3, t4, t5],
                process=Process.sequential
            )
            return str(crew.kickoff())

        except Exception as e:
            return (
                f"### 📋 Institutional Lesson Pack: {topic} ({grade_level})\n\n"
                f"**System Advisory:** The autonomous crew encountered an execution delay: `{str(e)[:140]}`\n\n"
                f"#### Core Objectives:\n"
                f"- Foundational concept mastery for {topic}.\n"
                f"- Formative assessment and interactive classroom practice.\n\n"
                f"#### 45-Minute Lesson Framework:\n"
                f"- **00-05 min:** Hook and prior knowledge activation.\n"
                f"- **05-20 min:** Explicit concept instruction.\n"
                f"- **20-35 min:** Hands-on guided collaborative task.\n"
                f"- **35-45 min:** Exit ticket and assessment recap."
            )

    # ... (Keep the rest of agent_service.py: run_timetable_audit_crew, run_attendance_intelligence_crew, run_id_card_credential_crew) ...
