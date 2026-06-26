from dotenv import load_dotenv
from graph.state import LearningState

load_dotenv()

from database.queries import (
    get_quiz_attempts_by_user,
    get_curriculum_by_user,
    get_user_by_telegram_id,
    mark_module_completed
)

def progress_tracker_agent(state: LearningState):
    telegram_id = state["telegram_id"]
    current_module = state.get("current_module", 1)
    quiz_score = state.get("quiz_score", 0)
    quiz_total = state.get("quiz_total", 5)

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {"response_message": "❌ User not found."}

    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        return {"response_message": "❌ No learning path setup found."}

    current_week = next(
        (w for w in curriculum if w["week_number"] == current_module),
        None
    )

    passed = quiz_score >= (quiz_total * 0.6)

    if passed and current_week and not current_week.get("is_completed", False):
        mark_module_completed(current_week["id"])
        current_week["is_completed"] = True  

    completed = [w for w in curriculum if w.get("is_completed", False)]
    completed_weeks = len(completed)
    total_weeks = len(curriculum)

    
    progress = (completed_weeks / total_weeks) * 100 if total_weeks > 0 else 0

    
    attempts = get_quiz_attempts_by_user(user_id)
    avg_score = 0
    if attempts:
        valid_attempts = 0
        total_percentage = 0
        for a in attempts:
            if a.get("total", 0) > 0:  
                total_percentage += (a["score"] / a["total"]) * 100
                valid_attempts += 1
        
        if valid_attempts > 0:
            avg_score = total_percentage / valid_attempts


    if passed and current_module < total_weeks:
        next_module = current_module + 1
    else:
        next_module = current_module

    response_message = (
        f"📊 <b>Progress Report</b>\n\n"
        f"📈 <b>Progress:</b> {progress:.0f}%\n"
        f"✅ <b>Completed Modules:</b> {completed_weeks}/{total_weeks}\n"
        f"📝 <b>Average Quiz Score:</b> {avg_score:.0f}%\n\n"
        f"{'🎉 <b>Module passed!</b> Moving to the next week.' if passed else '❌ <b>Score below 60%.</b> Please review materials and retry.'}\n\n"
        f"🎯 <b>Next Module:</b> Week {next_module}"
    )

    return {
        "completed_modules": [w["week_number"] for w in completed],
        "progress_report": response_message,
        "current_module": next_module,
        "response_message": response_message
    }