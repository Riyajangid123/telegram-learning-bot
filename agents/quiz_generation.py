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
    
    curriculum = state.get("curriculum", [])
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {
            "response_message": "User not found."
        }

    user_id = user["id"]
    db_curriculum = get_curriculum_by_user(user_id)

    if not curriculum and db_curriculum:
        curriculum = [
            {
                "week": w["week_number"],
                "title": w["tiitle"],
                "description": w["description"]
            }
            for w in db_curriculum
        ]

    if not curriculum:
        return {
            "response_message":
            "No curriculum found. Complete assessment first."
        }

    current_week = next(
        (w for w in curriculum if w["week"] == current_module),
        curriculum[0]
    )

    print("TOPIC:", topic)
    print("CURRENT WEEK:", current_week["title"])

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

        seen_questions = set()
        unique_questions = []
        
        for q in quiz_questions:
            question_text = q["question"].lower().strip()
            if question_text not in seen_questions:
                seen_questions.add(question_text)
                unique_questions.append(q)
            
        quiz_questions = unique_questions[:5] 
        print(f"✅ {len(quiz_questions)} unique questions generated")
        insert_quiz_questions(curriculum["id"],quiz_questions)
        
    except Exception as e:
        print(f"❌ Quiz parsing error: {str(e)}")
        quiz_questions = []

    message_lines = [
    f"🧠 Quiz Time! Week {current_module}: {current_week['title']}\n",
    "Answer all 5 questions!\n"
    ]

    for q in quiz_questions:
        message_lines.append(f"Q{q['id']}: {q['question']}")
        message_lines.append(f"A) {q['options']['A']}")
        message_lines.append(f"B) {q['options']['B']}")
        message_lines.append(f"C) {q['options']['C']}")
        message_lines.append(f"D) {q['options']['D']}\n")

    response_message = "\n".join(message_lines)
    response_message += "\nReply with your answers like: A B C D A"

    return {
    "quiz_questions": quiz_questions,
    "quiz_total": len(quiz_questions),
    "quiz_score": 0,
    "awaiting_quiz_answers": True,
    "response_message": response_message
    }