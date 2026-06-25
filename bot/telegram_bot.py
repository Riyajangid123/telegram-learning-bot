import os
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.ext import ApplicationBuilder

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
            
            final_state = await learning_graph.ainvoke(state)
            user_memory_cache[telegram_id] = final_state

    
            if final_state.get("response_message"):
                await update.message.reply_text(final_state["response_message"], parse_mode="HTML")

    except Exception as e:
        print(f"❌ Graph Error routing step: {e}")
        await update.message.reply_text("Something went wrong while compiling your roadmap details.")

import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def run_bot():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing!")

    application = ApplicationBuilder().token(TOKEN).build()
    

    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    PORT = int(os.getenv("PORT", 10000))

    if RENDER_URL:
        print(f"📡 Setting up passive Webhook tracking via: {RENDER_URL}")
        
    
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
    else:
        print("💻 Running locally via traditional polling...")
        application.run_polling()