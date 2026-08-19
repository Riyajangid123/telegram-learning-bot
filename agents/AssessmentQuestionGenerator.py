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
        You are an expert technical interviewer conducting a skill assessment.

        Generate EXACTLY 3 assessment questions to evaluate a learner's knowledge of:

        Topic:
        {topic}

        Session ID: {session_seed}

        Rules:

        - Questions must gradually increase in difficulty (easiest first, hardest last).
        - Cover a mix of conceptual understanding and practical/applied knowledge — not all questions should be theory-only.
        - Questions should be diagnostic: a learner's answer should clearly reveal whether they are at Beginner, Intermediate, Advanced, or Expert level.
        - Keep each question concise (1-2 sentences), unambiguous, and self-contained.
        - Do not provide answers, hints, or explanations — questions only.
        - Vary the phrasing, angle, and specific sub-concept each time this prompt runs, even for the same topic. Do not default to the most generic or "textbook" version of a question — approach the topic from a different angle than a typical assessment would (e.g., a real-world scenario, a common misconception, a comparison between two related concepts, or a "what would happen if..." framing).
        - Avoid reusing well-known example questions that appear frequently online for this topic.
        - Do not generate Python code.
        - Do not generate a Pydantic class.
        - Do not explain anything.
        """)

        self.chain = (
            self.prompt
            | self.llm.with_structured_output(
                AssessmentQuestions
            )
        )

    def assessment_question_generator(self,state:LearningState):

        result = self.chain.invoke({

            "topic": state["topic"],
            "session_seed":state["user_id"]

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