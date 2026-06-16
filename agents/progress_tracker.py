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
    user_id = user["id"]

    curriculum = get_curriculum_by_user(user_id)
    attempts = get_quiz_attempts_by_user(user_id)

    current_week = next(
    (w for w in curriculum if w["week_number"] == state["current_module"]),
    None)

    passed = quiz_score >= (quiz_total * 0.6)

    if passed and current_week:
        mark_module_completed(
            current_week["id"]
        )

    completed = [w for w in curriculum if w["is_completed"]]

    completed_weeks = len(completed)
    total_weeks = len(curriculum)

    avg_score = 0
    if attempts:
        avg_score = (
            sum(a["score"] / a["total"] * 100 for a in attempts)
            / len(attempts)
        )


    if passed and current_module < total_weeks:
        next_module = current_module + 1
    else:
        next_module = current_module


    response_message = f"""
    📊 Progress Report:
    ✅ Completed: {completed_weeks}/{total_weeks} modules
    📝 Quiz Average: {avg_score:.0f}%
    {'✅ Week passed! Moving to next module.' if passed else '❌ Score too low. Review and retry.'}
    🎯 Next: Week {current_module + 1 if passed else current_module}
        """

    return {
        "completed_modules": [w["week_number"] for w in completed],
        "progress_report": response_message,
        "next_module": str(next_module),
        "response_message": response_message
    }