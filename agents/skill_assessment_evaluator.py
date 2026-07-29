from graph.state import LearningState
from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import SkillAssessment
from database.queries import save_skill_assessment


class SkillAssessmentEvaluator:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
You are an expert AI Skill Assessment Agent.

Evaluate the learner.

Topic:
{topic}

Questions:
{questions}

User Answers:
{answers}

Assess:

1. Technical correctness
2. Completeness
3. Clarity
4. Practical understanding

Determine:

- Skill level
- Overall score
- Strengths
- Areas of improvement
- Summary
- Confidence

Rules:

- Be objective.
- Do not hallucinate.
- Give credit only for demonstrated knowledge.
- Skill level must be exactly one of:

Beginner
Intermediate
Advanced
Expert

- Score must be between 0 and 100.

Return ONLY the Pydantic schema.
""")

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                SkillAssessment
            )
        )

    def skill_assessment_evaluate(self, state: LearningState):

        assessment = self.chain.invoke({

            "topic": state["topic"],

            "questions": state["assessment_questions"],

            "answers": state["assessment_answers"]

        })

        state["skill_assessment"] = assessment

        save_skill_assessment(
            topic_id=state["topic_id"],
            assessment=assessment.model_dump()   
        )

        state["response_message"] = f"""
            ✅ Thank you for submitting your answers!

            Your responses have been analyzed successfully.

            🎯 Skill Level: {assessment.level}
            📊 Overall Score: {assessment.overall_score}/100

            I'm now creating your personalized learning roadmap...
            """

        state["phase"] = "learning_ready"
        print("skill assessment done!")
        return state