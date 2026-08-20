from langchain_core.prompts import ChatPromptTemplate
from agents.llm import LLM
from schema.schema import Quiz
from graph.state import LearningState
from database.queries import save_quiz
from html import escape

import random

import random

def shuffle_options(question):
    if question.type == "MCQ" and question.options:
        random.shuffle(question.options)
    return question

class QuizGenerationAgent:
    def __init__(self):
        self.llm = LLM().llm()

        self.quiz_prompt = ChatPromptTemplate.from_template("""
            You are an AI Quiz Generation Agent.

            Generate a quiz based STRICTLY on the topics in the curriculum's learning_path below.

            Curriculum:
            {curriculum}

            CRITICAL RULES:
            - Every question's `topic` field MUST be an EXACT topic name taken from
              curriculum.learning_path — do not invent, generalize, or substitute topics.
            - Do NOT create questions about generic categories like "Completeness",
              "Clarity", "Technical Correctness", or "Practical Understanding" unless
              one of those exact strings appears as a topic name in curriculum.learning_path.
              These are assessment-evaluation categories, not learning topics — never
              use them as quiz topics.
            - Only ask about concepts, skills, and knowledge areas that are explicitly
              part of the curriculum's learning_path topics.
            - Distribute questions across the curriculum topics — cover each topic at
              least once if total_questions allows.

            Question rules:
            - Match the learner's skill level when choosing question type:
              - Beginner topics: Mostly MCQs.
              - Intermediate topics: MCQs + Coding.
              - Advanced topics: Coding + Scenario questions.
            - Do not repeat questions.
            - Coding questions must not contain options.
            - MCQs must contain exactly four options.
            - Include a short explanation.
            - Difficulty should gradually increase across questions.
            - Every question should belong to exactly one curriculum topic (from learning_path).

            IMPORTANT — The `difficulty` field on each question MUST be
            exactly one of these three literal strings: "Easy", "Medium", "Hard".
            Do NOT use "Beginner", "Intermediate", or "Advanced" for this field.
            Map curriculum difficulty to question difficulty like this:
              - Beginner topic → mostly "Easy", some "Medium"
              - Intermediate topic → mostly "Medium", some "Hard"
              - Advanced topic → mostly "Hard"

            Return only data matching the provided structured output schema.
            Do not output Python code.
            Do not output the Pydantic class.
            Do not provide explanations outside the structured result..

        - For MCQ and TrueFalse questions, `correct_answer` MUST be the exact,
        verbatim text of the correct option as it appears in `options` —
        NEVER a letter like "A", "B", "C", or "D".
        - For Coding questions (no options), `correct_answer` should describe
        the expected correct output, approach, or key answer.""")
        
        self.chain = (
            self.quiz_prompt
            | self.llm.with_structured_output(Quiz,method="function_calling")
        )

    def quiz_generation(self, state: LearningState):

        quiz = self.chain.invoke({"curriculum": state["curriculum"]})

        for q in quiz.questions:
            shuffle_options(q)
            
        state["quiz"] = quiz
        state["phase"] = "awaiting_quiz_answers"

        formatted_quiz = "📝 <b>Quiz Time!</b>\n\n"

        for i, q in enumerate(quiz.questions, start=1):

            formatted_quiz += (
                f"<b>Q{i}. {escape(q.question)}</b>\n"
                f"Topic: {escape(q.topic)}\n"
                f"Difficulty: {escape(q.difficulty)}\n"
            )

            if q.options:
                for idx, option in enumerate(q.options):
                    formatted_quiz += (
                        f"{chr(65 + idx)}. {escape(option)}\n"
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