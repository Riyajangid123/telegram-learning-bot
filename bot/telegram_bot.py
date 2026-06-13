import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from graph.state import LearningState
from graph.workflow import build_graph
from database.queries import (
    insert_user,
    get_user_by_telegram_id,
    update_user_topic_skill_level,
    get_curriculum_by_user,
    insert_quiz_attempt,
    get_quiz_by_curriculum,
    get_resources_by_curriculum
)

load_dotenv()

workflow = build_graph()

user_stages = {}

active_quizzes = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    username = update.effective_user.username or "User"

    existing_user = get_user_by_telegram_id(telegram_id)

    if existing_user:
        if existing_user.get("topic") and existing_user.get("skill_level"):
            user_stages[telegram_id] = "curriculum_ready"
        else:
            user_stages[telegram_id] = "assessment"

        await update.message.reply_text(
            f"Welcome back {username}! 👋\n"
            f"Topic: {existing_user.get('topic', 'Not set')}\n"
            f"Level: {existing_user.get('skill_level', 'Not set')}\n\n"
            f"/learn — start new topic\n"
            f"/quiz  — take today's quiz\n"
            f"/progress — see your progress"
        )
    else:
        insert_user(telegram_id, username)
        user_stages[telegram_id] = "assessment"

        await update.message.reply_text(
            f"Welcome {username}! 🎓\n\n"
            f"What topic do you want to learn?\n"
            f"Example: Python, Machine Learning..."
        )

async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)

    if not user:
        await update.message.reply_text(
            "Please use /start first."
        )
        return

    user_id = user["id"]

    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        await update.message.reply_text(
            "No roadmap found. Use /learn first."
        )
        return

    topic = user.get("topic") or "Unknown"

    message = [
        f"🗺️ Learning Roadmap: {topic}\n"
    ]

    for week in curriculum:
        status = "✅" if week["is_completed"] else "⏳"

        message.append(
            f"{status} Week {week['week_number']}: "
            f"{week['module_title']}"
        )

    await update.message.reply_text(
        "\n".join(message)
    )

async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    user_stages[telegram_id] = "assessment"

    await update.message.reply_text(
        "What topic do you want to learn? 🎯\n"
        "Example: Python, Machine Learning, Web Development..."
    )

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)

    if not user:
        await update.message.reply_text(
            "Please /start first."
        )
        return

    curriculum = get_curriculum_by_user(user["id"])

    if not curriculum:
        await update.message.reply_text(
            "No curriculum found."
        )
        return

    current_week = next(
        (w for w in curriculum if not w["is_completed"]),
        curriculum[-1]
    )

    resources = get_resources_by_curriculum(current_week["id"])

    if not resources:
        await update.message.reply_text(
            "No resources available."
        )
        return

    message = [
        f"📚 Resources for Week {current_week['week_number']}:",
        f"{current_week['module_title']}\n"
    ]

    for resource in resources:

        icon = "📖"

        if resource["resource_type"] == "youtube":
            icon = "🎥"

        elif resource["resource_type"] == "course":
            icon = "🎓"

        message.append(
            f"{icon} {resource['title']}"
        )

        message.append(
            f"🔗 {resource['url']}\n"
        )

    await update.message.reply_text(
        "\n".join(message)
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text("Please /start first!")
        return

    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        await update.message.reply_text(
            "No curriculum found! Type /learn to create one first."
        )
        return


    current_week = next(
        (w for w in curriculum if not w["is_completed"]),
        curriculum[-1]
    )


    questions = get_quiz_by_curriculum(current_week["id"])

    if not questions:
        await update.message.reply_text(
            "No quiz available yet. Please wait for your curriculum to be ready!"
        )
        return

    
    active_quizzes[telegram_id] = {
        "questions": questions,
        "curriculum_id": current_week["id"],
        "user_id": user_id
    }


    user_stages[telegram_id] = "quiz"


    message_lines = [
        f"🧠 Quiz Time! Week {current_week['week_number']}: {current_week['module_title']}\n"
    ]

    for i, q in enumerate(questions):
        message_lines.append(f"Q{i+1}: {q['question']}")
        message_lines.append(f"A) {q['option_a']}")
        message_lines.append(f"B) {q['option_b']}")
        message_lines.append(f"C) {q['option_c']}")
        message_lines.append(f"D) {q['option_d']}\n")

    message_lines.append("Reply with answers like: A B C D A")

    await update.message.reply_text("\n".join(message_lines))



async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text("Please /start first!")
        return

    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        await update.message.reply_text("No curriculum found! Type /learn first.")
        return

    completed = [w for w in curriculum if w["is_completed"]]
    total = len(curriculum)
    done = len(completed)

    filled = int((done / total) * 10)
    bar = "█" * filled + "░" * (10 - filled)

    message = (
        f"📊 Your Progress Report\n\n"
        f"Topic: {user.get('topic','')}\n"
        f"Level: {user.get('skill_level','beginner')}\n\n"
        f"Progress: [{bar}] {done}/{total} weeks\n\n"
    )

    for week in curriculum:
        status = "✅" if week["is_completed"] else "⏳"
        message += f"{status} Week {week['week_number']}: {week['module_title']}\n"

    await update.message.reply_text(message)




async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    user_message = update.message.text

    user = get_user_by_telegram_id(telegram_id)

    if not user:
        await update.message.reply_text(
            "Please type /start first!"
        )
        return

    if telegram_id in user_stages:
        stage = user_stages[telegram_id]
    else:
        if not user.get("topic"):
            stage = "assessment"
        elif not user.get("skill_level"):
            stage = "assessment"
        else:
            stage = "curriculum_ready"
        
        user_stages[telegram_id] = stage

    print(f"DEBUG stage: {stage} for user {telegram_id}")

    if stage == "assessment":
        await handle_assessment(update, context, telegram_id, user_message)
    elif stage == "quiz":
        await handle_quiz_answer(update, context, telegram_id, user_message)
    else:
        await update.message.reply_text(
            "Use these commands:\n"
            "/learn — start new topic\n"
            "/quiz  — take today's quiz\n"
            "/progress — see your progress"
        )

async def handle_assessment(update, context, telegram_id, user_message):
    user = get_user_by_telegram_id(telegram_id)

    if not user:
        username = update.effective_user.username or "User"
        insert_user(telegram_id, username)
        user = get_user_by_telegram_id(telegram_id)

    state = {
        "telegram_id": telegram_id,
        "username": user.get("username") or "User",
        "topic": user_message,
        "user_message": user_message,
        "skill_level": "",
        "assessment_questions": [],
        "assessment_answers": [],
        "knowledge_gaps": [],
        "curriculum": [],
        "resources": {},
        "current_module": 1,
        "quiz_questions": [],
        "quiz_score": 0,
        "quiz_total": 0,
        "completed_modules": [],
        "quiz_scores": {},
        "progress_report": "",
        "next_module": "",
        "response_message": "",
        "messages": []
    }

    await update.message.reply_text("⏳ Assessing your skill level...")

    try:
        result = workflow.invoke(state)
        await update.message.reply_text(result["response_message"])

        user_stages[telegram_id] = "curriculum_ready"

    except Exception as e:
        print(f"❌ Workflow error: {str(e)}")
        await update.message.reply_text(
            f"Something went wrong: {str(e)}\n"
            "Please try again or type /learn"
        )

async def handle_quiz_answer(update, context, telegram_id, user_message):
    quiz_data = active_quizzes.get(telegram_id)

    if not quiz_data:
        await update.message.reply_text("No active quiz. Type /quiz to start one!")
        return

    questions = quiz_data["questions"]
    curriculum_id = quiz_data["curriculum_id"]
    user_id = quiz_data["user_id"]

    answers = user_message.strip().upper().split()

    if len(answers) != len(questions):
        await update.message.reply_text(
            f"Please send exactly {len(questions)} answers!\n"
            f"Example: A B C D A"
        )
        return


    score = 0
    result_lines = ["📝 Quiz Results:\n"]

    for i, q in enumerate(questions):
        correct = q["correct_ans"]
        user_ans = answers[i] if i < len(answers) else "?"
        is_correct = user_ans == correct

        if is_correct:
            score += 1
            result_lines.append(f"Q{i+1}: ✅ Correct!")
        else:
            result_lines.append(
                f"Q{i+1}: ❌ Wrong! "
                f"Correct answer: {correct}"
            )

    total = len(questions)
    percentage = (score / total) * 100

    result_lines.append(f"\n🎯 Score: {score}/{total} ({percentage:.0f}%)")

    if percentage >= 60:
        result_lines.append("✅ Passed! Moving to next module tomorrow.")
    else:
        result_lines.append("❌ Keep studying! You can retry tomorrow.")

   
    insert_quiz_attempt(
        user_id=user_id,
        curriculum_id=curriculum_id,
        score=score,
        total=total
    )

    
    del active_quizzes[telegram_id]
    user_stages[telegram_id] = "chat"

    await update.message.reply_text("\n".join(result_lines))


def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("roadmap", roadmap))
    app.add_handler(CommandHandler("resources", resources))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()