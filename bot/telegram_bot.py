from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from graph.workflow import build_graph
from bot.scheduler import setup_scheduler
import os

learning_graph = build_graph()

user_memory_cache = {}

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_chat.id
    username = update.effective_user.username or "Learner"
    incoming_text = update.message.text

    if telegram_id not in user_memory_cache:
        user_memory_cache[telegram_id] = {
            "messages": [],
            "telegram_id": telegram_id,
            "username": username,
            "topic": incoming_text,
            "user_message": incoming_text,
            "skill_level": "",
            "assessment_questions": [],
            "assessment_answers": [],
            "knowledge_gaps": [],
            "curriculum": [],
            "resources": {},
            "user_answers": [],
            "awaiting_topic":False,
            "awaiting_quiz_answers": False,
            "current_module": 1,
            "quiz_questions": [],
            "quiz_score": 0,
            "quiz_total": 5,
            "completed_modules": [],
            "quiz_scores": {},
            "progress_report": "",
            "next_module": 1,
            "response_message": ""
        }
    else:
        user_memory_cache[telegram_id]["user_message"] = ""
        
        if incoming_text.startswith("/"):
            user_memory_cache[telegram_id]["user_message"] = ""

    updated_state = await learning_graph.ainvoke(user_memory_cache[telegram_id])
    
    user_memory_cache[telegram_id] = updated_state

    final_reply = updated_state.get("response_message", "Processing...")
    
    await update.message.reply_text(final_reply)

def run_bot():
    token=os.getenv("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(MessageHandler(filters.TEXT | filters.COMMAND, telegram_message_handler))

    setup_scheduler(user_memory_cache)

    print("scheduler is running inside bot...")
    
    print("🚀 Centralized LangGraph Controller Engine running on Telegram...")
    app.run_polling(drop_pending_updates=True)