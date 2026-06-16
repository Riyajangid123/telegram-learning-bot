from graph.workflow import LearningState
from database.queries import (insert_quiz_attempt,get_user_by_telegram_id,
                              get_curriculum_by_user,get_quiz_by_curriculum)

def quiz_evaluator_agent(state:LearningState):
    telegram_id=state["telegram_id"]
    user_answers = state["user_answers"]

    
    user=get_user_by_telegram_id(telegram_id)
    user_id=user["id"]

    curriculum=get_curriculum_by_user(user_id)

    current_week = next(
    (w for w in curriculum if w["week_number"] == state["current_module"]),
    None)

    curriculum_id=current_week["id"]

    quiz_questions = get_quiz_by_curriculum(curriculum_id)

    score = 0

    for i, q in enumerate(quiz_questions):
        if i < len(user_answers):
            if user_answers[i].upper() == q["correct_ans"].upper():
                score += 1


    insert_quiz_attempt(user_id,curriculum_id,score,len(quiz_questions))

    return {
        "quiz_score": score,
        "awaiting_quiz_answers": False,
        "response_message": f"🏆 Score: {score}/{len(quiz_questions)}"
    }