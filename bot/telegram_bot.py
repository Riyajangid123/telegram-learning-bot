import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes
from telegram import BotCommand 

from graph.workflow import build_graph
from database.queries import insert_user, get_user_by_telegram_id

graph_app = build_graph()
user_sessions = {}

def initialize_user_state(telegram_id: int, username: str):
    """
    Ensures ALL keys required by your agents exist in the state stringently
    to prevent future KeyErrors down the pipeline.
    """
    return {
        "messages": [],
        "telegram_id": telegram_id,
        "username": username,
        "topic": "",
        "skill_level": "beginner",  
        "knowledge_gaps": [],       
        "phase": "awaiting_topic",
        "curriculum": [],
        "resources": {},
        "response_message": "",
        "user_message": ""
    }

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or f"User_{user_id}"

    try:
        existing_user = get_user_by_telegram_id(user_id)
        if not existing_user:
            print(f"👤 User {user_id} not found in DB. Automatically registering...")
            insert_user(telegram_id=user_id, username=username)
            print("✅ User saved successfully!")
    except Exception as e:
        print(f"⚠️ Database automatic registration warning: {e}")

    initial_state = initialize_user_state(user_id, username)
    initial_state["user_message"] = "/start"
    initial_state["phase"] = "start"
    
    output_state = graph_app.invoke(initial_state)
    user_sessions[user_id] = dict(output_state)
    
    intro_text = output_state.get("response_message", "Something went wrong.")
    await update.message.reply_text(intro_text, parse_mode="HTML")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    username = update.effective_user.username or f"User_{user_id}"
    
    if user_id not in user_sessions:
        try:
            if not get_user_by_telegram_id(user_id):
                insert_user(telegram_id=user_id, username=username)
        except Exception as e:
            print(f"⚠️ Middle-step DB verification fallback error: {e}")
            
        user_sessions[user_id] = initialize_user_state(user_id, username)
        
    current_state = user_sessions[user_id]
    current_state["user_message"] = user_text
    current_state["telegram_id"] = user_id
    
    
    output_state = graph_app.invoke(current_state)
    user_sessions[user_id] = dict(output_state)
    
    if output_state.get("response_message"):
        await update.message.reply_text(output_state["response_message"], parse_mode="HTML")
        

    if output_state.get("phase") == "assessment_complete":
        print("🚀 Assessment finished! Sending intermediate status and running curriculum/search...")
        
        await update.message.reply_text(
            "🛠️ <b>Generating your personalized weekly curriculum & looking up active web resources...</b>\n"
            "<i>I am querying Groq and using DuckDuckGo to scrape top video links and tutorials. Please hold on a brief moment...</i>", 
            parse_mode="HTML"
        )
        
        output_state["phase"] = "learning"
        await context.bot.send_chat_action(chat_id=user_id, action="typing")
        
        final_state = graph_app.invoke(output_state)
        user_sessions[user_id] = dict(final_state)
        
        if final_state.get("response_message"):
            await update.message.reply_text(final_state["response_message"], parse_mode="HTML")


def run_bot():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing!")

    application = ApplicationBuilder().token(TOKEN).build()

    async def set_commands(app):
        commands = [
            BotCommand("start", "Initialize the bot and select a topic"),
            BotCommand("quiz", "Take a quiz on your current learning module"),
            BotCommand("progress", "Check your syllabus progress status")
        ]
        await app.bot.set_my_commands(commands)

    application.post_init = set_commands

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
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