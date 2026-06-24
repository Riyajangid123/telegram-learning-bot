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


async def telegram_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Handles every Telegram message.
    """
    if not update.message:
        return

    telegram_id = update.effective_chat.id
    username = update.effective_user.username or "Learner"
    incoming_text = update.message.text.strip()

    if incoming_text == "/start":
        user_memory_cache[telegram_id] = initialize_user_state(telegram_id, username)
        insert_user(telegram_id, username)
        
        welcome_message = (
            "👋 <b>Welcome to AI Learning Bot!</b>\n\n"
            "I'm your personal AI learning assistant.\n\n"
            "🚀 <b>Here's how I can help you:</b>\n"
            "✅ Assess your current skill level\n"
            "✅ Create a personalized learning roadmap\n"
            "✅ Recommend resources\n"
            "✅ Generate quizzes\n"
            "✅ Track progress\n\n"
            "📚 <b>What would you like to learn today?</b>\n\n"
            "Examples:\n"
            "• Python\n"
            "• Machine Learning\n"
            "• SQL\n"
            "• Data Structures"
        )

        await update.message.reply_text(welcome_message, parse_mode="HTML")
        return

    insert_user(telegram_id, username)

    print("=" * 60)
    print(f"📩 Message from {telegram_id}: {incoming_text}")

    if telegram_id not in user_memory_cache:
        user_memory_cache[telegram_id] = initialize_user_state(
            telegram_id,
            username
        )

    state = user_memory_cache[telegram_id]
    state["user_message"] = incoming_text

    print("\nINPUT STATE")
    print(state)

    
    is_completing_assessment = state.get("phase") == "assessment" and len(state.get("assessment_answers", [])) == 4

    try:
        updated_state = await learning_graph.ainvoke(state)
        state.update(updated_state)
        user_memory_cache[telegram_id] = state

        print("\nUPDATED STATE (STEP 1)")
        print(state)

        final_response = state.get("response_message", "Something went wrong.")

        placeholder_msg = await update.message.reply_text(
            final_response,
            parse_mode="HTML"
        )

        if is_completing_assessment or state.get("phase") == "learning" and not state.get("resources"):
            print("🚀 Launching background DuckDuckGo Resource Finder...")
            
            
            await context.bot.send_chat_action(chat_id=telegram_id, action="typing")
            
           
            updated_resource_state = await learning_graph.ainvoke(state)
            state.update(updated_resource_state)
            user_memory_cache[telegram_id] = state
            
            print("\nUPDATED STATE (STEP 2 - Resource Search Completed)")
            print(state)
            
            final_resource_response = state.get("response_message", "Something went wrong.")
            
            await context.bot.edit_message_text(
                chat_id=telegram_id,
                message_id=placeholder_msg.message_id,
                text=final_resource_response,
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"❌ Graph Error: {e}")
        error_fallback = "Something went wrong while processing your request."
        await update.message.reply_text(error_fallback)


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