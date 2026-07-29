from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import Quiz
from graph.state import LearningState
from database.queries import save_quiz

class QuizGenerationAgent:
    def __init__(self):
        self.llm = LLM().llm()

        self.quiz_prompt = ChatPromptTemplate.from_template("""
            You are an AI Quiz Generation Agent.

            Generate a quiz from the provided curriculum.

            Curriculum:
            {curriculum}

            Rules:
            - Questions must come only from the curriculum.
            - Match the learner's skill level.
            - Beginner: Mostly MCQs.
            - Intermediate: MCQs + Coding.
            - Advanced: Coding + Scenario questions.
            - Do not repeat questions.
            - Coding questions must not contain options.
            - MCQs must contain exactly four options.
            - Include a short explanation.
            - Difficulty should gradually increase.
            - Every question should belong to one curriculum topic.

            Return ONLY the Pydantic schema.
            """)

        self.chain = (
            self.quiz_prompt
            | self.llm.with_structured_output(Quiz)
        )

    def quiz_generation(self, state: LearningState):

        quiz = self.chain.invoke({
            "curriculum": state["curriculum"]
        })

        state["quiz"] = quiz
        state["phase"] = "awaiting_quiz_answers"

        formatted_quiz = "📝 <b>Quiz Time!</b>\n\n"

        for i, q in enumerate(quiz.questions, start=1):

            formatted_quiz += (
                f"<b>Q{i}. {q.question}</b>\n"
                f"Topic: {q.topic}\n"
                f"Difficulty: {q.difficulty}\n"
            )

            if q.options:
                for idx, option in enumerate(q.options):
                    formatted_quiz += (
                        f"{chr(65 + idx)}. {option}\n"
                    )

            formatted_quiz += "\n"

        formatted_quiz += (
            "\n📝 Reply with your answers in this format:\n\n"
            "1. A\n"
            "2. C\n"
            "3. Python uses indentation\n"
            "4. B\n"
            "...\n\n"
            "After you submit your answers, I'll evaluate them and show your progress."
        )

        state["response_message"] = formatted_quiz
        state["phase"] = "awaiting_quiz_answers"
        quiz_id = save_quiz(
            curriculum_id=state["curriculum_id"],
            quiz=quiz.model_dump()               
        )

        state["quiz_id"] = quiz_id

        print("Quiz generated successfully.")

        return state