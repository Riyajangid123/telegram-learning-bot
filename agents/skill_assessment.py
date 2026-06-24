from graph.state import LearningState
from database.queries import update_user_topic_skill_level, get_user_by_telegram_id
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import os

load_dotenv()

def skill_assesment_agent(state: LearningState):
    greetings = {
    "hi",
    "hello",
    "hey",
    "hii",
    "good morning",
    "good evening",
    "good afternoon"
}

    if state.get("phase") == "awaiting_topic":

        message = state["user_message"].strip().lower()

        if message in greetings:
            return {
                "response_message":
                    "👋 Hello!\n\nWhat topic would you like to learn?\n\nExamples:\n• Python\n• Machine Learning\n• SQL",
                "phase": "awaiting_topic"
            }

        topic = message

        first_question = f"What do you already know about {topic}?"

        return {
            "topic": topic,
            "phase": "assessment",
            "assessment_questions": [first_question],
            "assessment_answers": [],
            "response_message":
                f"Great! Let's learn {topic}. 🚀\n\n"
                f"I'll first assess your knowledge.\n\n"
                f"Question 1:\n{first_question}"
        }

    telegram_id = state["telegram_id"]
    topic = state["topic"]
    user_message = state["user_message"]

    assessment_questions = list(state.get("assessment_questions", []))
    assessment_answers = list(state.get("assessment_answers", []))

    model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        api_key=os.getenv("GROQ_API_KEY")
    )

    question_prompt = ChatPromptTemplate.from_template("""
        You are a skill assessment expert.

        Topic: {topic}

        Questions:
        {questions}

        Answers:
        {answers}

        Ask ONLY the next assessment question.

        Rules:
        - Ask exactly one new question.
        - Do not evaluate the user.
        - Do not return JSON.
        """)

    evaluation_prompt = ChatPromptTemplate.from_template("""
        You are a skill assessment expert.

        Topic: {topic}

        Questions:
        {questions}

        Answers:
        {answers}

        Evaluate the user's knowledge.

        Return ONLY valid JSON:

        {{
        "skill_level": "beginner",
        "knowledge_gaps": [
            "...",
            "..."
        ]
        }}
        """)

    chain1=question_prompt|model
    chain2=evaluation_prompt|model


    if user_message and user_message != topic:
        assessment_answers.append(user_message)

    if len(assessment_questions) == 5 and len(assessment_answers) == 5:

        response = chain2.invoke({
            "topic": topic,
            "questions": assessment_questions,
            "answers": assessment_answers
        })

        clean = response.content.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            return {
                "response_message": "I couldn't evaluate your answers. Please try again."
            }

    
        skill_level = data["skill_level"]
        gaps = data["knowledge_gaps"]

    
        update_user_topic_skill_level(
            telegram_id=telegram_id,
            topic=topic,
            skill_level=skill_level
        )

        return {
            "skill_level": skill_level,
            "knowledge_gaps": gaps,
            "assessment_answers": assessment_answers,
            "assessment_questions": assessment_questions,
            "phase": "learning",
            "response_message": response.content
        }

    else:

        response = chain1.invoke({
            "topic": topic,
            "questions": assessment_questions,
            "answers": assessment_answers
        })

        assessment_questions.append(response.content)

        return {
            "skill_level": "",
            "knowledge_gaps": [],
            "phase": "assessment",
            "assessment_answers": assessment_answers,
            "assessment_questions": assessment_questions,
            "response_message": response.content
        }