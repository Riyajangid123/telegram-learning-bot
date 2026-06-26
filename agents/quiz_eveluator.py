from graph.state import LearningState
from database.queries import (insert_quiz_attempt, get_user_by_telegram_id,
                              get_curriculum_by_user, get_quiz_by_curriculum)

def quiz_evaluator_agent(state: LearningState):
    telegram_id = state["telegram_id"]
    user_answers_input = state.get("user_answers", [])

    if isinstance(user_answers_input, str):
        user_answers = user_answers_input.strip().split()
    else:
        user_answers = [str(ans).strip() for ans in user_answers_input]

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {"response_message": "❌ Error: Profile not found during grading."}
    
    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    current_week = next(
        (w for w in curriculum if w["week_number"] == state.get("current_module", 1)),
        None
    )

    if not current_week:
        return {"response_message": "❌ Error: Current module structure not found."}

    curriculum_id = current_week["id"]
    quiz_questions = get_quiz_by_curriculum(curriculum_id)

    if not quiz_questions:
        return {"response_message": "❌ Error: Could not find quiz questions to evaluate against."}

    score = 0

    for i, q in enumerate(quiz_questions):
        if i < len(user_answers):
            correct_answer = q.get("correct", q.get("correct_ans", "")).strip().upper()
            
            if user_answers[i].upper() == correct_answer:
                score += 1

    insert_quiz_attempt(user_id, curriculum_id, score, len(quiz_questions))

    feedback_msg = (
        f"🏆 <b>Quiz Evaluation Completed!</b>\n\n"
        f"📊 Your Score: <b>{score} / {len(quiz_questions)}</b>\n"
        f"<i>Great job! You can type /progress to see your updated completion chart or ask me any follow-up questions about this module.</i>"
    )

    return {
        "quiz_score": score,
        "quiz_total": len(quiz_questions),
        "awaiting_quiz_answers": False,
        "response_message": feedback_msg
    }