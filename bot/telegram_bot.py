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
from graph.workflow import build_graph


graph_app = build_graph()

user_phases = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    initial_state = {
        "user_message": "/start",
        "phase": "start",
        "telegram_id": user_id  
    }
    
    output_state = graph_app.invoke(initial_state)
    intro_text = output_state.get("response_message", "Something went wrong.")
    await update.message.reply_text(intro_text)

    await update.message.reply_text(intro_text, parse_mode="HTML")



user_sessions = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    current_state = user_sessions.get(user_id, {
        "phase": "awaiting_topic",
        "topic": "",
        "telegram_id": user_id
    })
    
    
    current_state["user_message"] = user_text
    current_state["telegram_id"] = user_id
    

    output_state = graph_app.invoke(current_state)
    
    user_sessions[user_id] = dict(output_state)
    
    reply_text = output_state.get("response_message", "Processing...")
    await update.message.reply_text(reply_text, parse_mode="HTML")


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def run_bot():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing!")

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    

    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    PORT = int(os.getenv("PORT", 10000))

    if RENDER_URL:
        print(f"📡 Webhook linked successfully! Listening on root path...")
        

        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/",
            webhook_url=f"{RENDER_URL}/"
        )

    else:
        print("💻 Running locally via traditional polling...")
        application.run_polling()