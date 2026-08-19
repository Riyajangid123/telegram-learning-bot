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

        Evaluate the learner's knowledge of:

        Topic:
        {topic}

        Questions:
        {questions}

        User Answers:
        {answers}

        INTERNAL SCORING RUBRIC (use these 4 dimensions only to judge quality —
        do NOT output these dimension names anywhere in your response):

        1. Technical correctness — is the answer factually/technically accurate?
        2. Completeness — does the answer cover what was asked, fully?
        3. Clarity — is the answer well-explained and understandable?
        4. Practical understanding — does the learner show applied, real-world grasp?

        CRITICAL — Naming rule for strengths / areas_of_improvement:
        - NEVER use the rubric dimension names themselves ("Technical Correctness",
          "Completeness", "Clarity", "Practical Understanding") as a strength or
          area of improvement.
        - Instead, name the SPECIFIC concept, sub-topic, or skill within "{topic}"
          that the learner is strong or weak in.
          Example (if topic is "Python"): strengths might be "variable declaration",
          "basic loops"; areas_of_improvement might be "recursion", "exception handling",
          "object-oriented design" — never generic rubric words.
        - Every strength and area_of_improvement MUST be a real, specific concept
          that belongs to "{topic}", something that could plausibly become a
          curriculum topic or quiz subject on its own.

        Determine:

        - Skill level
        - Overall score
        - Strengths (specific {topic} concepts only — see rule above)
        - Areas of improvement (specific {topic} concepts only — see rule above)
        - Summary
        - Confidence

        Rules:

        - Be objective. Base every judgment strictly on the User Answers provided above —
          never assume competence that wasn't demonstrated.
        - Do not hallucinate.
        - Give credit only for demonstrated knowledge.
        - CRITICAL: If User Answers is empty, blank, missing, contains only placeholder
          text, or does not actually answer the questions asked, you MUST NOT default
          to "Intermediate" or any other mid-level guess. In this case:
            - Set skill_level to "Beginner"
            - Set score to 0
            - Set confidence to "Low"
            - State clearly in the summary that no valid answers were provided,
              so assessment could not be meaningfully performed.
        - Do not treat an unanswered or skipped question as partial credit.
        - Skill level must be exactly one of:

        Beginner
        Intermediate
        Advanced
        Expert

        - Score must be between 0 and 100.

        Return only data matching the provided structured output schema.
        Do not output Python code.
        Do not output the Pydantic class.
        Do not provide explanations outside the structured result.
        """)

        
        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                SkillAssessment,method="json_schema"
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