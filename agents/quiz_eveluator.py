from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import QuizEvaluation
from graph.state import LearningState
from database.queries import save_quiz_attempt

class QuizEvaluationAgent:
    def __init__(self):
        self.llm=LLM().llm()
        self.evaluation_prompt = ChatPromptTemplate.from_template("""
            You are an AI Quiz Evaluator.

            Quiz:
            {quiz}

            User Answers:
            {answers}

            Evaluate every question.

            Instructions

            - Compare user answer with correct answer.
            - Award marks.
            - Explain mistakes.
            - Identify weak topics.
            - Identify strengths.
            - Recommend revision topics.

            Return only data matching the provided structured output schema.
            Do not output Python code.
            Do not output the Pydantic class.
            Do not provide explanations outside the structured result..
            """)

        self.chain = (
            self.evaluation_prompt
            | self.llm.with_structured_output(
                QuizEvaluation,method="json_schema"
            )
        )

    def evaluate(self, state:LearningState):

        evaluation = self.chain.invoke({

            "quiz": state["quiz"],

            "answers": state["user_answers"]

        })

        state["quiz_evaluation"] = evaluation
        
        percentage = round((evaluation.score / evaluation.total_questions) * 100, 1) if evaluation.total_questions else 0

        state["response_message"] = (
            f"🎉 Great job completing the quiz!\n\n"
            f"🏆 Score: {evaluation.score}/{evaluation.total_questions}\n"
            f"📈 Accuracy: {percentage}%\n\n"
            f"Now type <b>/progress</b> to view your complete learning report, strengths, weak areas, and recommendations."
        )

        state["phase"] = "quiz_completed"
        save_quiz_attempt(
            quiz_id=state["quiz_id"],
            user_id=state["user_id"],
            answers=state["user_answers"],
            evaluation=evaluation.model_dump(),  
            score=evaluation.score
        )

        state["phase"] = "idle"

        return state