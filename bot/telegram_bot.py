import os
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

from graph.workflow import build_graph
from bot.scheduler import setup_scheduler
from database.queries import insert_user

learning_graph = build_graph()

user_memory_cache = {}


def initialize_user_state(telegram_id: int, username: str):
    """
    Creates the initial state for a new user.
    """
    return {
        "messages": [],
        "telegram_id": telegram_id,
        "username": username,

        # Learning
        "topic": "",
        "skill_level": "",
        "knowledge_gaps": [],
        "phase": "awaiting_topic",

        # Assessment
        "assessment_questions": [],
        "assessment_answers": [],

        # Curriculum
        "curriculum": [],
        "resources": {},

        # Quiz
        "quiz_questions": [],
        "user_answers": [],
        "awaiting_quiz_answers": False,
        "quiz_score": 0,
        "quiz_total": 0,

        # Progress
        "current_module": 1,
        "completed_modules": [],
        "quiz_scores": {},
        "progress_report": "",
        "next_module": 1,

        # Response
        "response_message": "",
        "user_message": ""
    }


async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user_text = update.message.text.strip()

    if telegram_id not in user_memory_cache:
        user_memory_cache[telegram_id] = {
            "telegram_id": telegram_id,
            "user_message": user_text,
            "phase": "awaiting_topic",
            "assessment_questions": [],
            "assessment_answers": [],
            "messages": []
        }
    
    state = user_memory_cache[telegram_id]
    state["user_message"] = user_text

    try:
        updated_state = await learning_graph.ainvoke(state)
        state.update(updated_state)
        user_memory_cache[telegram_id] = state


        if state.get("response_message"):
            await update.message.reply_text(state["response_message"], parse_mode="HTML")

        if state.get("phase") == "assessment_complete":
            print("🚀 Assessment finished! Advancing to Curriculum & Resource Planner Agents...")
            
            state["phase"] = "learning"
            
            await context.bot.send_chat_action(chat_id=telegram_id, action="typing")
            await update.message.reply_text("🛠️ <b>Generating your personalized weekly curriculum & looking up active web resources...</b>", parse_mode="HTML")
            
            final_learning_state = await learning_graph.ainvoke(state)
            state.update(final_learning_state)
            user_memory_cache[telegram_id] = state

    
            if state.get("response_message"):
                await update.message.reply_text(state["response_message"], parse_mode="HTML")

    except Exception as e:
        print(f"❌ Graph Error routing step: {e}")
        await update.message.reply_text("Something went wrong while compiling your roadmap details.")

def run_bot():
    """
    Starts Telegram bot.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found.")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.COMMAND,
            telegram_message_handler,
        )
    )

    setup_scheduler(user_memory_cache)

    print("=" * 60)
    print("🤖 AI Learning Bot Started")
    print("=" * 60)

    app.run_polling(drop_pending_updates=True)