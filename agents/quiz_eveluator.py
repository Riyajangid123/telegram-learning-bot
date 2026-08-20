from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import QuizEvaluation
from graph.state import LearningState
from database.queries import save_quiz_attempt

class QuizEvaluationAgent:
    def __init__(self):
        self.llm = LLM().llm()

        self.evaluation_prompt = ChatPromptTemplate.from_template("""
            You are an AI Quiz Evaluator.

            Quiz:
            {quiz}

            User Answers:
            {answers}

            IMPORTANT — how to interpret user answers:
            - For MCQ / TrueFalse questions, the user's answer may be a single
              letter (A, B, C, D) referring to the POSITION of an option in
              that question's `options` list (A = 1st option, B = 2nd option,
              C = 3rd option, D = 4th option).
            - Map the letter to the corresponding option text using that
              question's own `options` array, THEN compare that resolved
              option text against `correct_answer` to judge correctness.
            - `correct_answer` always contains the exact text of the correct
              option — never a letter. Do not compare a raw letter directly
              against `correct_answer`.
            - For Coding / free-text questions (no options), compare the
              user's answer text directly against `correct_answer` and
              `explanation`, judging on meaning rather than exact wording.
            - If a question has no matching user answer, treat it as
              unanswered/incorrect and award 0 marks for it.

            Evaluate every question.

            Instructions

            - Compare user answer with correct answer using the mapping rules above.
            - Award marks.
            - Explain mistakes.
            - Identify weak topics.
            - Identify strengths.
            - Recommend revision topics.

            Return only data matching the provided structured output schema.
            Do not output Python code.
            Do not output the Pydantic class.
            Do not provide explanations outside the structured result.
            """)

        self.chain = (
            self.evaluation_prompt
            | self.llm.with_structured_output(
                QuizEvaluation, method="function_calling"
            )
        )

    def evaluate(self, state: LearningState):

        if not state.get("user_answers"):
            state["response_message"] = (
                "📊 I don't have any answers to evaluate yet.\n\n"
                "Please submit your quiz answers first, then I'll evaluate them."
            )
            return state

        try:
            evaluation = self.chain.invoke({
                "quiz": state["quiz"],
                "answers": state["user_answers"]
            })

        except Exception as e:
            print(f"Quiz evaluation failed: {e}")
            state["response_message"] = (
                "❌ <b>Quiz evaluation failed.</b>\n\n"
                "I couldn't evaluate your answers right now. Please try submitting them again."
            )
            return state

        state["quiz_evaluation"] = evaluation

        percentage = (
            round((evaluation.score / evaluation.total_questions) * 100, 1)
            if evaluation.total_questions else 0
        )

        state["response_message"] = (
            f"🎉 Great job completing the quiz!\n\n"
            f"🏆 Score: {evaluation.score}/{evaluation.total_questions}\n"
            f"📈 Accuracy: {percentage}%\n\n"
            f"Now type <b>/progress</b> to view your complete learning report, strengths, weak areas, and recommendations."
        )

        state["phase"] = "idle"

        try:
            save_quiz_attempt(
                quiz_id=state["quiz_id"],
                user_id=state["user_id"],
                answers=state["user_answers"],
                evaluation=evaluation.model_dump(),
                score=evaluation.score
            )
        except Exception as e:
            print(f"Failed to save quiz attempt: {e}")

        return state