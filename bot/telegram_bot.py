import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from graph.workflow import build_graph
from graph.state import LearningState

from database.queries import (
    create_user,
    get_user,
    get_session,
    update_session,
    create_learning_topic,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

workflow = build_graph()

user_sessions = {}

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

# Start dummy server in background thread
threading.Thread(target=run_dummy_server, daemon=True).start()


def default_state(user, username) -> LearningState:
    """
    user = row returned from get_user()
    """

    return {
        "messages": [],

        "user_id": user[0],
        "telegram_id": user[1],
        "username": username,

        "topic": "",
        "topic_id": None,

        "user_message": "",

        "phase": "",

        "assessment_questions": [],
        "assessment_answers": [],
        "skill_assessment": None,

        "curriculum": None,
        "curriculum_id": None,

        "resources": None,

        "quiz": None,
        "quiz_id": None,

        "user_answers": [],
        "quiz_evaluation": None,

        "progress": None,

        "response_message": "",
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.effective_user.id
    username = update.effective_user.username or ""

    create_user(
        telegram_id=telegram_id,
        username=username,
    )

    user = get_user(telegram_id)

    state = default_state(user, username)

    state["user_message"] = "/start"

    result = workflow.invoke(state)

    user_sessions[telegram_id] = result

    update_session(
        user_id=result["user_id"],
        phase=result["phase"],
        topic_id=None,
    )

    await update.message.reply_text(
        result["response_message"],
        parse_mode="HTML",
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.effective_user.id
    username = update.effective_user.username or ""
    message = update.message.text.strip()

    user = get_user(telegram_id)

    if user is None:

        create_user(telegram_id, username)
        user = get_user(telegram_id)

    if telegram_id in user_sessions:

        state = user_sessions[telegram_id]

    else:

        state = default_state(user, username)

        session = get_session(state["user_id"])

        if session:

            state["phase"] = session[0]
            state["topic_id"] = session[1]

    state["user_message"] = message

    if state["phase"] == "awaiting_topic":
        state["topic"] = message
        topic_id = create_learning_topic(state["user_id"], message)
        state["topic_id"] = topic_id

    if message == "/resources":
        await update.message.reply_text(
            "🔎 <b>Searching for the best resources for you...</b>\n\n"
            "📄 Looking through articles\n"
            "🎥 Finding YouTube tutorials\n"
            "🎓 Checking free courses\n\n"
            "This may take a moment ⏳",
            parse_mode="HTML",
        )
    elif message == "/quiz":
        await update.message.reply_text(
            "📝 <b>Generating your quiz...</b>\n\n"
            "Crafting questions tailored to your curriculum ✍️",
            parse_mode="HTML",
        )
    elif message == "/progress":
        await update.message.reply_text(
            "📊 <b>Analyzing your progress...</b>\n\n"
            "Reviewing your assessment, curriculum, and quiz results 🔍",
            parse_mode="HTML",
        )

    result = workflow.invoke(state)

    user_sessions[telegram_id] = result

    update_session(
        user_id=result["user_id"],
        phase=result["phase"],
        topic_id=result.get("topic_id"),
    )

    await update.message.reply_text(
        result["response_message"],
        parse_mode="HTML",
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Something went wrong finding resources — please try /resources again in a moment."
        )


def run_bot():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(CommandHandler("resources", message_handler))
    application.add_handler(CommandHandler("quiz", message_handler))
    application.add_handler(CommandHandler("progress", message_handler))

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler,
        )
    )
     
    application.add_error_handler(error_handler)
    print("🚀 AI Learning Bot Started")

    application.run_polling()