from database.queries import (get_curriculum_by_user, get_user_by_telegram_id, 
insert_quiz_questions,get_quiz_by_curriculum)

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json
import os
from graph.state import LearningState
from dotenv import load_dotenv

load_dotenv()

def quiz_generation_agent(state: LearningState):
    model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY")
    )

    current_module = state.get("current_module", 1)
    telegram_id = state["telegram_id"]
    topic = state.get("topic", "")
    skill_level = state.get("skill_level", "beginner")
    
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {"response_message": "User not found."}

    user_id = user["id"]
    db_curriculum = get_curriculum_by_user(user_id)

    db_current_week = next(
        (w for w in db_curriculum if w["week_number"] == current_module),
        None
    )

    if not db_current_week:
        return {"response_message": "Current week not found."}

    curriculum_id = db_current_week["id"]
    
    week_title = db_current_week.get("module_title", db_current_week.get("title", f"Week {current_module}"))

    prompt = ChatPromptTemplate.from_template("""
        You are a quiz generator expert.

        Generate 5 MCQ questions for:
        Topic: {topic}
        Current Week: {week_title}
        Skill Level: {skill_level}
        
        Rules:
        - Questions must be based on {week_title} only
        - ALL 5 questions must be completely different from each other
        - 4 options per question (A, B, C, D)
        - Only ONE correct answer per question
        - Wrong options should be believable, not obvious
        - Match difficulty to {skill_level}
        
        Return ONLY this JSON, nothing else:
        {{
            "questions": [
                {{
                    "id": 1,
                    "question": "What is the difference between list and tuple?",
                    "options": {{
                        "A": "Lists are mutable, tuples are immutable",
                        "B": "Tuples are mutable, lists are immutable",
                        "C": "Both are mutable",
                        "D": "Both are immutable"
                    }},
                    "correct": "A",
                    "explanation": "Lists can be modified after creation, tuples cannot"
                }}
            ]
        }}
    """)  

    chain = prompt | model
    existing_questions = get_quiz_by_curriculum(curriculum_id)

    if existing_questions:
        message_lines = [
            f"🧠 <b>Quiz Time! Week {current_module}: {week_title}</b>\n",
            "Answer all questions.\n"
        ]

        for i, q in enumerate(existing_questions, start=1):
            message_lines.append(f"<b>Q{i}.</b> {q['question']}")
            message_lines.append(f"A) {q['option_a']}")
            message_lines.append(f"B) {q['option_b']}")
            message_lines.append(f"C) {q['option_c']}")
            message_lines.append(f"D) {q['option_d']}\n")

        message_lines.append("📥 <i>Reply like: A B C D A</i>")

        return {
            "quiz_questions": existing_questions,
            "quiz_total": len(existing_questions),
            "quiz_score": 0,
            "awaiting_quiz_answers": True,
            "response_message": "\n".join(message_lines)
        }

    response = chain.invoke({
        "topic": topic,
        "week_title": week_title, 
        "skill_level": skill_level
    })

    clean = response.content.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean)
    quiz_questions = data.get("questions", [])

    unique_questions = []
    seen = set()

    for q in quiz_questions:
        key = q["question"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_questions.append(q)

    quiz_questions = unique_questions

    if len(quiz_questions) != 5:
        return {"response_message": "Unable to generate a complete quiz. Please try again."}
    
    insert_quiz_questions(curriculum_id, quiz_questions)

    message_lines = [
        f"🧠 <b>Quiz Time! Week {current_module}: {week_title}</b>\n",
        "Answer all questions.\n"
    ]

    for q in quiz_questions:
        message_lines.append(f"<b>Q{q['id']}.</b> {q['question']}")
        message_lines.append(f"A) {q['options']['A']}")
        message_lines.append(f"B) {q['options']['B']}")
        message_lines.append(f"C) {q['options']['C']}")
        message_lines.append(f"D) {q['options']['D']}\n")

    message_lines.append("📥 <i>Reply like: A B C D A</i>")

    return {
        "quiz_questions": quiz_questions,
        "quiz_total": len(quiz_questions),
        "quiz_score": 0,
        "awaiting_quiz_answers": True,
        "response_message": "\n".join(message_lines)
    }