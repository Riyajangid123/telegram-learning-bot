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
            f"👋 <b>Welcome {username} to your AI Learning Assistant!</b>\n\n"
            "What topic or skill would you like to master today?\n"
            "<i>Just type the topic name below to begin your path!</i>"
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

    is_finding_resources = state.get("phase") == "assessment_complete" or (
        len(state.get("assessment_answers", [])) >= len(state.get("assessment_questions", [])) 
        if state.get("assessment_questions") else False
    )

    placeholder_msg = None
    if is_finding_resources:
        placeholder_msg = await update.message.reply_text(
            "⏳ <i>Analyzing your answers and researching tailored learning links... This will take a moment.</i>",
            parse_mode="HTML"
        )

    try:
        updated_state = await learning_graph.ainvoke(state)
        state.update(updated_state)
        user_memory_cache[telegram_id] = state

        print("\nUPDATED STATE")
        print(state)

        final_response = state.get("response_message", "Something went wrong.")

        if placeholder_msg:
            await context.bot.edit_message_text(
                chat_id=telegram_id,
                message_id=placeholder_msg.message_id,
                text=final_response,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                final_response,
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"❌ Graph Error: {e}")
        error_fallback = "Something went wrong while processing your request."
        
        if placeholder_msg:
            await context.bot.edit_message_text(
                chat_id=telegram_id,
                message_id=placeholder_msg.message_id,
                text=error_fallback
            )
        else:
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