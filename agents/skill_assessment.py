from graph.state import LearningState
from database.queries import update_user_topic_skill_level, get_user_by_telegram_id
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

def skill_assessment_agent(state: LearningState):
    greetings = {
        "hi", "hello", "hey", "hii", 
        "good morning", "good evening", "good afternoon"
    }

    if state.get("phase") == "awaiting_topic":
        message = state["user_message"].strip().lower()

        if message in greetings:
            return {
                "response_message": "👋 Hello!\n\nWhat topic would you like to learn?\n\nExamples:\n• Python\n• Machine Learning\n• SQL",
                "phase": "awaiting_topic"
            }

        topic = message
        first_question = f"What do you already know about {topic}?"

        return {
            "topic": topic,
            "phase": "assessment",
            "assessment_questions": [first_question],
            "assessment_answers": [],
            "response_message": (
                f"Great! Let's learn {topic.upper()}. 🚀\n\n"
                f"I'll first ask you 5 quick questions to gauge your level.\n\n"
                f"<b>Question 1:</b>\n{first_question}"
            )
        }

    telegram_id = state["telegram_id"]
    topic = state["topic"]
    user_message = state["user_message"]

    assessment_questions = list(state.get("assessment_questions", []))
    assessment_answers = list(state.get("assessment_answers", []))

    model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
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
        You are a strict backend API data generator. You output ONLY JSON.
        Do not include any conversational introductions, markdown blocks, or text outside the JSON structure.

        Topic: {topic}
        Questions: {questions}
        Answers: {answers}

        Evaluate the user's knowledge. Return ONLY valid JSON matching this exact format:
        {{
            "skill_level": "beginner",
            "knowledge_gaps": ["topic1", "topic2"]
        }}
        """)

    chain1 = question_prompt | model
    chain2 = evaluation_prompt | model

    if user_message and user_message.lower() != topic.lower():
        assessment_answers.append(user_message)

    if len(assessment_questions) <= len(assessment_answers):
        response = chain2.invoke({
            "topic": topic,
            "questions": assessment_questions,
            "answers": assessment_answers
        })

        clean = response.content.replace("```json", "").replace("```", "").strip()
        
        try:
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
            if json_match:
                clean = json_match.group(0)
            data = json.loads(clean)
        except Exception:
            return {
                "response_message": "⚠️ I couldn't process the skill evaluation. Let's restart this step cleanly."
            }

        skill_level = data.get("skill_level", "beginner")
        gaps = data.get("knowledge_gaps", [])

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
            "phase": "assessment_complete",
            "response_message": f"📊 <b>Evaluation Completed!</b>\n\nAssessed Tier: <b>{skill_level.capitalize()}</b>\nAnalyzing your roadmap metrics now..."
        }

    else:
        response = chain1.invoke({
            "topic": topic,
            "questions": assessment_questions,
            "answers": assessment_answers
        })

        assessment_questions.append(response.content)
        q_num = len(assessment_questions)

        return {
            "skill_level": "",
            "knowledge_gaps": [],
            "phase": "assessment",
            "assessment_answers": assessment_answers,
            "assessment_questions": assessment_questions,
            "response_message": f"<b>Question {q_num}:</b>\n{response.content}"
        }