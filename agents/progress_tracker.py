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
        return {
            "response_message": "User not found."
        }

    user_id = user["id"]

    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        return {
            "response_message": "No curriculum found."
        }

    attempts = get_quiz_attempts_by_user(user_id)

    current_week = next(
        (w for w in curriculum if w["week_number"] == current_module),
        None
    )

    passed = quiz_score >= (quiz_total * 0.6)

    if passed and current_week and not current_week["is_completed"]:
        mark_module_completed(current_week["id"])

    completed = [w for w in curriculum if w["is_completed"]]

    completed_weeks = len(completed)
    total_weeks = len(curriculum)

    progress = (completed_weeks / total_weeks) * 100

    avg_score = 0
    if attempts:
        avg_score = sum(
            a["score"] / a["total"] * 100
            for a in attempts
        ) / len(attempts)

    if passed and current_module < total_weeks:
        next_module = current_module + 1
    else:
        next_module = current_module

    response_message = f"""
        📊 Progress Report

        📈 Progress: {progress:.0f}%

        ✅ Completed Modules: {completed_weeks}/{total_weeks}

        📝 Average Quiz Score: {avg_score:.0f}%

        {'✅ Module passed! Moving to the next week.' if passed else '❌ Score below 60%. Please review and retry.'}

        🎯 Next Module: Week {next_module}
        """

    return {
        "completed_modules": [w["week_number"] for w in completed],
        "progress_report": response_message,
        "current_module": next_module,
        "next_module": next_module,
        "response_message": response_message
    }