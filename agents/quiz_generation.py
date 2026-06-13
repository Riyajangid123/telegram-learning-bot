from database.queries import get_curriculum_by_user, get_user_by_telegram_id, insert_quiz_questions
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

    curriculum = state.get("curriculum", [])
    current_module = state.get("current_module", 1)
    telegram_id = state["telegram_id"]
    topic = state.get("topic", "")
    skill_level = state.get("skill_level", "beginner")

   
    current_week = next(
        (w for w in curriculum if w["week"] == current_module),
        curriculum[0] if curriculum else {"week": 1, "title": topic}
    )

    prompt = ChatPromptTemplate.from_template("""
        You are a quiz generator expert.

        Generate 5 MCQ questions for:
        Topic: {topic}
        Current Week: {week_title}
        Skill Level: {skill_level}
        
        Rules:
        - Questions must be based on {week_title} only
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

    response = chain.invoke({
        "topic": topic,
        "week_title": current_week["title"],  
        "skill_level": skill_level
    })

    try:
        clean = response.content.strip()
        clean = clean.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        quiz_questions = data["questions"]
    except Exception as e:
        print(f"❌ Quiz parsing error: {str(e)}")
        quiz_questions = []


    user = get_user_by_telegram_id(telegram_id)
    user_id = user["id"]
    db_curriculum = get_curriculum_by_user(user_id)

    db_current_week = next(
        (w for w in db_curriculum if w["week_number"] == current_module),
        db_curriculum[0] if db_curriculum else None
    )

    if db_current_week and quiz_questions:
        insert_quiz_questions(
            curriculum_id=db_current_week["id"], 
            questions=quiz_questions
        )

    message_lines = [
        f"🧠 Quiz Time! Week {current_module}: {current_week['title']}\n",
        f"Answer all 5 questions!\n"
    ]

    for q in quiz_questions:
        message_lines.append(f"Q{q['id']}: {q['question']}")
        message_lines.append(f"A) {q['options']['A']}")
        message_lines.append(f"B) {q['options']['B']}")
        message_lines.append(f"C) {q['options']['C']}")
        message_lines.append(f"D) {q['options']['D']}\n")

    response_message = "\n".join(message_lines)
    response_message += "Reply with your answers like: A B C D A"

    return {
        "quiz_questions": quiz_questions,
        "quiz_total": len(quiz_questions),
        "quiz_score": 0,
        "response_message": response_message
    }