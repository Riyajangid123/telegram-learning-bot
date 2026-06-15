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
from bot.scheduler import setup_scheduler
from agents.skill_assessment import skill_assesment_agent
from graph.state import LearningState
from graph.workflow import build_graph
from database.queries import (
    insert_user,
    get_user_by_telegram_id,
    update_user_topic_skill_level,
    get_curriculum_by_user,
    insert_quiz_attempt,
    get_quiz_by_curriculum,
    get_resources_by_user_and_week,
    mark_module_completed
)

load_dotenv()

workflow = build_graph()

user_stages = {}
active_quizzes = {}
assessment_sessions = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    username = update.effective_user.username or "User"

    print("START CALLED")
    print("CHAT ID:", telegram_id)

    existing_user = get_user_by_telegram_id(telegram_id)
    print("EXISTING USER:", existing_user)

    if existing_user:
        if existing_user.get("topic") and existing_user.get("skill_level"):
            user_stages[telegram_id] = {"stage": "learning"}
        else:
            user_stages[telegram_id] = {"stage": "assessment"}

        await update.message.reply_text(
            f"Welcome back {username}! 👋\n"
            f"Topic: {existing_user.get('topic', 'Not set')}\n"
            f"Level: {existing_user.get('skill_level', 'Not set')}\n\n"
            f"/learn — start new topic\n"
            f"/quiz  — take today's quiz\n"
            f"/roadmap — view learning roadmap\n"
            f"/resources — get study materials\n"
            f"/progress — see your progress"
        )
    else:
        insert_user(telegram_id, username)
        print("INSERTING USER")
        print("telegram_id =", telegram_id)
        
        user_stages[telegram_id] = {"stage": "topic"}

        await update.message.reply_text(
            f"Welcome {username}! 🎓\n\n"
            f"I am an AI-driven Learning Assistant designed to build custom curriculums. "
            f"Before we begin, here is how our workflow works:\n\n"
            f"🔍 1. **Skill Assessment**: Once you pick a topic, I will ask you a few screening questions to evaluate your current understanding.\n"
            f"📊 2. **Gap Analysis**: My core agent will analyze your strengths and knowledge gaps.\n"
            f"🗺️ 3. **Roadmap Generation**: I will generate a fully customized weekly roadmap, complete with resources and quizzes tailored exactly to your level.\n\n"
            f"To kick off this process, **what topic do you want to master today?**\n"
            f"*(Example: Python, Machine Learning, Data Structures)*"
        )


async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text("Please use /start first.")
        return

    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        await update.message.reply_text("No roadmap found. Use /learn first.")
        return

    topic = user.get("topic") or "Unknown"
    message = [f"🗺️ Learning Roadmap: {topic}\n"]

    for week in curriculum:
        status = "✅" if week["is_completed"] else "⏳"
        message.append(
            f"{status} Week {week['week_number']}: {week['module_title']}"
        )

    await update.message.reply_text("\n".join(message))


async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    user_stages[telegram_id] = {"stage": "topic"}

    await update.message.reply_text("📚 What topic do you want to learn?")


async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)
    user_id=user["id"]
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return

    curriculum = get_curriculum_by_user(user["id"])
    if not curriculum:
        await update.message.reply_text("No curriculum found.")
        return

    current_week = next(
        (w for w in curriculum if not w["is_completed"]),
        curriculum[-1]
    )

    res_list = get_resources_by_user_and_week(user_id,current_week["week_number"])
    if not res_list:
        await update.message.reply_text("No resources available.")
        return

    message = [
        f"📚 Resources for Week {current_week['week_number']}:",
        f"{current_week['module_title']}\n"
    ]

    for resource in res_list:
        icon = "📖"
        if resource["resource_type"] == "youtube":
            icon = "🎥"
        elif resource["resource_type"] == "course":
            icon = "🎓"

        message.append(f"{icon} {resource['title']}")
        message.append(f"🔗 {resource['url']}\n")

    await update.message.reply_text("\n".join(message))


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text("Please use /start first!")
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

    user_stages[telegram_id] = {"stage": "quiz"}

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
        await update.message.reply_text("Please use /start first!")
        return

    user_id = user["id"]
    curriculum = get_curriculum_by_user(user_id)

    if not curriculum:
        await update.message.reply_text("No curriculum found! Type /learn first.")
        return

    completed = [w for w in curriculum if w["is_completed"]]
    total = len(curriculum)
    done = len(completed)

    filled = int((done / total) * 10) if total > 0 else 0
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
    username = update.effective_user.username or "User"
    text = update.message.text.strip()

    if telegram_id not in user_stages:
        existing_user = get_user_by_telegram_id(telegram_id)
        
        if existing_user:
            if existing_user.get("topic") and existing_user.get("skill_level"):
                user_stages[telegram_id] = {"stage": "learning"}
            else:
                user_stages[telegram_id] = {"stage": "assessment"}
        else:
            user_stages[telegram_id] = {"stage": "start"}

    current_stage_data = user_stages[telegram_id]
    stage = current_stage_data.get("stage") if isinstance(current_stage_data, dict) else current_stage_data

    if stage == "start":
        await update.message.reply_text("👋 Hello! Please initialize the bot properly by typing /start.")
        
    elif stage == "topic":
        await handle_topic(update, telegram_id, username, text)

    elif stage == "assessment":
        await handle_assessment(update, telegram_id, username, text)

    elif stage == "quiz":
        await handle_quiz_answer(update, context, telegram_id, text)

    elif stage == "learning":
        await update.message.reply_text(
            "🧠 I'm listening! If you want to interact, use my commands:\n\n"
            "/roadmap — view your path\n"
            "/resources — study material\n"
            "/quiz — take a test\n"
            "/progress — view weekly stats\n"
            "/learn — switch topics"
        )
    else:
        user_stages[telegram_id] = {"stage": "start"}
        await update.message.reply_text("Something went out of sync. Please type /start to refresh.")

async def handle_topic(update, telegram_id, username, topic):
    state = {
        "telegram_id": telegram_id, "username": username, "topic": topic,
        "user_message": "", "assessment_questions": [], "assessment_answers": [],
        "knowledge_gaps": [], "curriculum": [], "resources": {},
        "current_module": 1, "quiz_questions": [], "quiz_score": 0,
        "quiz_total": 0, "completed_modules": [], "quiz_scores": {},
        "progress_report": "", "next_module": "", "response_message": "",
        "messages": []
    }

    result = skill_assesment_agent(state)

    user_stages[telegram_id] = {
        "stage": "assessment",
        "state": {**state, **result}
    }

    await update.message.reply_text(result["response_message"])


async def handle_assessment(update, telegram_id, username, answer):
    state = user_stages[telegram_id]["state"]
    state["user_message"] = answer

    result = skill_assesment_agent(state)
    state.update(result)

    if result["skill_level"] == "":
        user_stages[telegram_id]["state"] = state
        await update.message.reply_text(result["response_message"])
        return

    await update.message.reply_text("⏳ Creating your roadmap...")
    print("STATE TELEGRAM ID:", state.get("telegram_id"))

    final_state = workflow.invoke(state)
    user_stages[telegram_id] = {"stage": "learning"}

    await update.message.reply_text(final_state["response_message"])


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
            f"Please send exactly {len(questions)} answers!\nExample: A B C D A"
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
            result_lines.append(f"Q{i+1}: ❌ Wrong! Correct answer: {correct}")

    total = len(questions)
    percentage = (score / total) * 100

    result_lines.append(f"\n🎯 Score: {score}/{total} ({percentage:.0f}%)")

    if percentage >= 60:
        result_lines.append("✅ Passed! Moving to next module tomorrow.")
        mark_module_completed(curriculum_id)
    else:
        result_lines.append("❌ Keep studying! You can retry tomorrow.")

    insert_quiz_attempt(
        user_id=user_id, curriculum_id=curriculum_id, score=score, total=total
    )

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(CommandHandler("roadmap", roadmap))
    app.add_handler(CommandHandler("resources", resources))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    async def post_init(application):
        setup_scheduler(user_stages,active_quizzes)
        print("⏰ Scheduler started inside bot!")

    app.post_init = post_init

    print("🤖 Bot is running...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
