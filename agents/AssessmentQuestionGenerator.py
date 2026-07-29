from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from graph.state import LearningState
from pydantic import BaseModel, Field
from typing import List


class AssessmentQuestions(BaseModel):
    questions: List[str] = Field(
        description="Exactly three assessment questions."
    )


class AssessmentQuestionGeneratorAgent:

    def __init__(self):

        self.llm = LLM().llm()

        self.prompt = ChatPromptTemplate.from_template("""
        You are an expert technical interviewer.

        Generate EXACTLY 3 assessment questions to evaluate a learner's knowledge of:

        Topic:
        {topic}

        Rules:

        - Questions should gradually increase in difficulty.
        - Cover both conceptual and practical understanding.
        - Questions should help determine whether the learner is:
            Beginner
            Intermediate
            Advanced
            Expert
        - Keep questions short and clear.
        - Do not provide answers.
        - Return ONLY the Pydantic schema.
        """)

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                AssessmentQuestions
            )
        )

    def assessment_question_generator(self,state:LearningState):

        result = self.chain.invoke({

            "topic": state["topic"]

        })

        state["assessment_questions"] = result.questions

        state["phase"] = "awaiting_assessment_answers"

        questions = "\n\n".join(

            f"{i+1}. {q}"

            for i, q in enumerate(result.questions)

        )

        state["response_message"] = (
            f"Let's assess your knowledge of {state['topic']}.\n\n"
            "Please answer the following questions:\n\n"
            f"{questions}"
        )

        return state