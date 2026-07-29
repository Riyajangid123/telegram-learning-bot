from langchain_core.prompts import ChatPromptTemplate
from schema.schema import CurriculumPlan
from agents.llm import LLM
from graph.state import LearningState
from database.queries import save_curriculum

class CurriculumPlanner:
    def __init__(self):
        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
            You are an expert AI Curriculum Planner.

            Create a personalized learning roadmap based on the following skill assessment.

            Skill Assessment:
            {skill_assessment}

            Guidelines:
            - Tailor the curriculum according to the learner's current level.
            - Prioritize weak areas first.
            - Arrange topics from foundational to advanced.
            - Include learning objectives and practice tasks.
            - If the learner is Beginner, do not assign a capstone project.
            - If the learner is Intermediate or above, include an appropriate capstone project.
            - Keep the roadmap practical and realistic.

            If learner level is Beginner,
            return capstone_project as null.

            Return ONLY the Pydantic schema.
            """)
        
        self.structured_llm = self.llm.with_structured_output(CurriculumPlan)
        self.chain = self.prompt | self.structured_llm

    def curriculum_generation(self,state:LearningState):
        try:
            result = self.chain.invoke({
                "skill_assessment": state["skill_assessment"]
            })

            state["curriculum"] = result
            print("Curriculum generated successfuly",state["curriculum"])
            curriculum_id = save_curriculum(
                topic_id=state["topic_id"],
                curriculum=result.model_dump()  
            )

            state["curriculum_id"] = curriculum_id
            roadmap = []

            for i, topic in enumerate(result.learning_path, start=1):
                roadmap.append(
                    f"{i}. {topic.topic} ({topic.difficulty})"
                )

            state["response_message"] = f"""
            🎉 Your personalized curriculum is ready!

            Target Level: {result.target_level}

            Roadmap

            {chr(10).join(roadmap)}

            Estimated Hours: {result.total_estimated_hours}

            Commands

            /quiz → Take a quiz

            I'm now finding the best articles, videos and free courses for each topic...

            Good luck with your learning journey! 🚀
            """

        except Exception as e:
            print(f"Curriculum generation failed: {e}")
            state["curriculum"] = None

        return state