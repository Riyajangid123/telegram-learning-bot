import os
from datetime import date
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import Bot
from database.queries import (
    get_all_active_users,
    get_curriculum_by_user,
    get_resources_by_user_and_week,
    get_quiz_by_curriculum,
    get_quiz_attempts_by_user,
    insert_daily_log,
    update_lesson_sent,
    update_quiz_sent,
    lesson_already_sent,
    quiz_already_sent
)

load_dotenv()
user_memory_cache = {}

def get_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment!")
    return Bot(token=token)


async def send_daily_lesson():
    bot = get_bot()
    print("📚 Sending daily lessons...")

    users = get_all_active_users()

    for user in users:
        try:
            telegram_id = user["telegram_id"]
            user_id = user["id"]

            curriculum = get_curriculum_by_user(user_id)
            if not curriculum:
                continue

            current_week = next(
                (w for w in curriculum if not w.get("is_completed", False)),
                None
            )

            if not current_week:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "🎉 <b>Congratulations! You completed your entire curriculum!</b>\n\n"
                        "Type a new topic to start learning something new!"
                    ),
                    parse_mode="HTML"
                )
                continue

            resources = get_resources_by_user_and_week(
                user_id=user_id,
                week_number=current_week["week_number"]
            )

            week_title = current_week.get("title") or current_week.get("module_title", "No Title")
            week_desc = current_week.get("description") or current_week.get("module_desc", "")

            message_lines = [
                "🌅 <b>Good Morning! Today's Lesson:</b>\n",
                f"📅 <b>Week {current_week['week_number']}:</b> {week_title}",
                f"📝 <i>{week_desc}</i>\n",
                "📚 <b>Recommended Learning Resources:</b>"
            ]

            if resources:
                for r in resources:
                    res_type = r.get("resource_type", "youtube").lower()
                    if "youtube" in res_type:
                        icon = "🎥"
                    elif "article" in res_type or "doc" in res_type:
                        icon = "📖"
                    else:
                        icon = "🎓"

                    message_lines.append(f"{icon} <a href='{r['url']}'>{r['title']}</a>")
            else:
                message_lines.append("• <i>No specific resource links saved for this week. Check your master plan block!</i>")

            message_lines.append(
                "\n⏰ <b>Quiz time at 8:00 PM tonight!</b>\n"
                "Good luck with today's learning! 💪"
            )

            today = date.today()

            if lesson_already_sent(user_id, current_week["id"], today):
                print(f"ℹ️ Lesson already sent today to {telegram_id}")
                continue

            await bot.send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines),
                parse_mode="HTML"
            )

            insert_daily_log(
                user_id=user_id,
                curriculum_id=current_week["id"],
                sent_date=today
            )
            update_lesson_sent(
                user_id=user_id,
                curriculum_id=current_week["id"],
                sent_date=today
            )
            
            print(f"✅ Lesson sent cleanly to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending lesson to {user.get('telegram_id')}: {str(e)}")
            continue


async def send_evening_quiz():
    bot = get_bot()
    print("🧠 Sending evening quizzes...")

    users = get_all_active_users()

    for user in users:
        try:
            telegram_id = user["telegram_id"]
            user_id = user["id"]

            curriculum = get_curriculum_by_user(user_id)
            if not curriculum:
                continue

            current_week = next(
                (w for w in curriculum if not w.get("is_completed", False)),
                None
            )

            if not current_week:
                continue

            questions = get_quiz_by_curriculum(current_week["id"])
            if not questions:
                await bot.send_message(
                    chat_id=telegram_id,
                    text="No quiz available for today. Keep studying! 📚",
                    parse_mode="HTML"
                )
                continue

            week_title = current_week.get("title") or current_week.get("module_title", "No Title")

            message_lines = [
                "🧠 <b>Evening Quiz Time!</b>\n",
                f"📅 <b>Week {current_week['week_number']}:</b> {week_title}\n"
            ]

            for i, q in enumerate(questions):
                message_lines.append(f"<b>Q{i+1}:</b> {q['question']}")
                message_lines.append(f"A) {q['option_a']}")
                message_lines.append(f"B) {q['option_b']}")
                message_lines.append(f"C) {q['option_c']}")
                message_lines.append(f"D) {q['option_d']}\n")

            message_lines.append("👉 <i>Reply with your answers matching this format precisely: A B C D A</i>")

            today = date.today()

            if quiz_already_sent(user_id, current_week["id"], today):
                print(f"ℹ️ Quiz already sent today to {telegram_id}")
                continue

            await bot.send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines),
                parse_mode="HTML"
            )

            update_quiz_sent(
                user_id,
                current_week["id"],
                today
            )

            if telegram_id not in user_memory_cache:
                user_memory_cache[telegram_id] = {}

            user_memory_cache[telegram_id].update({
                "quiz_questions": questions,
                "quiz_total": len(questions),
                "awaiting_quiz_answers": True,
                "current_module": current_week["week_number"],
                "next_module": current_week["week_number"]
            })

            print(f"✅ Quiz active and sent to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending quiz to {user.get('telegram_id')}: {str(e)}")
            continue


async def send_weekly_report():
    bot = get_bot()
    print("📊 Sending weekly reports...")

    users = get_all_active_users()

    for user in users:
        try:
            telegram_id = user["telegram_id"]
            user_id = user["id"]

            curriculum = get_curriculum_by_user(user_id)
            raw_attempts = get_quiz_attempts_by_user(user_id)
            attempts = list(raw_attempts) if raw_attempts else []

            if not curriculum:
                continue

            completed = [w for w in curriculum if w.get("is_completed", False)]
            pending = [w for w in curriculum if not w.get("is_completed", False)]
            total_weeks = len(curriculum)
            completed_weeks = len(completed)

            filled = int((completed_weeks / total_weeks) * 10) if total_weeks else 0
            bar = "█" * filled + "░" * (10 - filled)

            if len(attempts) > 0:
                total_percentage = 0
                for a in attempts:
                    total_q = a.get("total", 1) or 1 
                    total_percentage += (a.get("score", 0) / total_q) * 100
                avg_score = total_percentage / len(attempts)
            else:
                avg_score = 0

            next_week = pending[0] if pending else None

            message_lines = [
                "📊 <b>Weekly Progress Report</b>\n",
                f"👤 <b>Topic:</b> {user.get('topic', 'Not set')}",
                f"🎯 <b>Level:</b> {str(user.get('skill_level', 'beginner')).capitalize()}\n",
                f"Progress: <code>[{bar}]</code> {completed_weeks}/{total_weeks} weeks",
                f"📝 Quiz Average: <b>{avg_score:.0f}%</b>\n",
                "📋 <b>Curriculum Overview:</b>"
            ]

            for week in curriculum:
                status = "✅" if week.get("is_completed") else "⏳"
                w_title = week.get("title") or week.get("module_title", "No Title")
                message_lines.append(f"  {status} Week {week['week_number']}: {w_title}")

            if next_week:
                next_title = next_week.get("title") or next_week.get("module_title", "No Title")
                message_lines.append(f"\n📌 <b>Next Up:</b> Week {next_week['week_number']} - {next_title}")
                message_lines.append("\nKeep going! You're doing great! 🚀")
            else:
                message_lines.append("\n🎉 <b>You completed everything! Type a new topic name to begin!</b>")

            await bot.send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines),
                parse_mode="HTML"
            )

            print(f"✅ Progress report sent to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending report to {user.get('telegram_id')}: {str(e)}")
            continue


def setup_scheduler(memory_cache):
    global user_memory_cache
    user_memory_cache = memory_cache

    ist = timezone("Asia/Kolkata")
    scheduler = AsyncIOScheduler(timezone=ist)
    
    scheduler.add_job(
        send_daily_lesson,
        CronTrigger(hour=9, minute=0, timezone=ist),
        id="daily_lesson",
        name="Send Daily Lesson",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.add_job(
        send_evening_quiz,
        CronTrigger(hour=20, minute=0, timezone=ist),
        id="evening_quiz_job",
        name="Send Evening Quiz",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.add_job(
        send_weekly_report,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=ist),
        id="weekly_report",
        name="Send Weekly Report",
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()
    print("⏰ Scheduler started cleanly!")
    print("  📚 Daily lesson  → 9:00 AM IST")
    print("  🧠 Evening quiz  → 8:00 PM IST")
    print("  📊 Weekly report → Sunday 10:00 AM IST")

    return scheduler