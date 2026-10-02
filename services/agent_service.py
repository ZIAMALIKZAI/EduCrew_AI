import time
from crewai import Crew, Task, Process
from agents.teacher_agents import TeacherCrewAgents

class AgentService:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.agent_factory = TeacherCrewAgents(model_name=model_name)

    def run_lesson_planning_workflow(self, topic: str, grade_level: str, context_text: str = "") -> str:
        planner = self.agent_factory.curriculum_planner_agent()
        assessor = self.agent_factory.assessment_specialist_agent()
        differentiator = self.agent_factory.student_support_agent()

        t1 = Task(
            description=(
                f"Develop a complete 45-minute lesson plan for Topic: '{topic}' at Grade Level: '{grade_level}'. "
                f"Reference Content: {context_text[:1500] if context_text else 'Standard curriculum'}. "
                "Include learning goals, direct instruction steps, interactive work, and assessment check."
            ),
            expected_output="A structured 45-minute lesson plan with clear timing.",
            agent=planner
        )

        t2 = Task(
            description=(
                f"Based on the lesson plan for '{topic}', create a 5-question quiz with an answer key "
                "and an analytic rubric (Levels: Beginning, Proficient, Advanced)."
            ),
            expected_output="5 quiz questions with answers and a 3-tier grading rubric.",
            agent=assessor
        )

        t3 = Task(
            description=(
                f"Review the lesson and assessment for '{topic}'. Provide 2 remedial modifications for struggling "
                "learners and 2 extension activities for advanced students."
            ),
            expected_output="Remedial modifications and enrichment extension activities.",
            agent=differentiator
        )

        crew = Crew(
            agents=[planner, assessor, differentiator],
            tasks=[t1, t2, t3],
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Enforces a rate limit so Google does not drop calls with 503/429
        )

        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            # If default model still throttles, try fallback model
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                fallback_model = "gemini-1.5-pro" if "flash" in self.model_name else "gemini-1.5-flash"
                time.sleep(3)
                fallback_factory = TeacherCrewAgents(model_name=fallback_model)
                fallback_crew = Crew(
                    agents=[
                        fallback_factory.curriculum_planner_agent(),
                        fallback_factory.assessment_specialist_agent(),
                        fallback_factory.student_support_agent()
                    ],
                    tasks=[t1, t2, t3],
                    process=Process.sequential,
                    max_rpm=10
                )
                return str(fallback_crew.kickoff())
            raise e
