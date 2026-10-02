from crewai import Agent
from core.gemini import get_llm

class TeacherCrewAgents:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.llm = get_llm(model_name=model_name)

    def curriculum_planner_agent(self) -> Agent:
        return Agent(
            role="Curriculum & Lesson Designer",
            goal="Design pedagogy-aligned lesson plans, weekly objectives, and engaging teaching flows.",
            backstory="Experienced instructional designer who breaks down topics into 45-minute lesson blocks.",
            llm=self.llm,
            verbose=True,
            memory=False
        )

    def assessment_specialist_agent(self) -> Agent:
        return Agent(
            role="Assessment & Quiz Specialist",
            goal="Create rubrics, formative quizzes, Bloom's Taxonomy assessments, and answer keys.",
            backstory="Evaluation expert designing diagnostic and summative assessments with scoring rubrics.",
            llm=self.llm,
            verbose=True,
            memory=False
        )

    def student_support_agent(self) -> Agent:
        return Agent(
            role="Differentiated Learning Coach",
            goal="Adapt materials for diverse classroom needs, remedial learners, and enrichment tracks.",
            backstory="Inclusive education specialist tailoring lesson content for different learning paces.",
            llm=self.llm,
            verbose=True,
            memory=False
        )
