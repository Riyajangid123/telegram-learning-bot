import os
import asyncio
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import Bot
from bot.telegram_bot import user_stages
from bot.telegram_bot import active_quizzes
from database.queries import (
    get_all_active_users,
    get_curriculum_by_user,
    get_resources_by_user_and_week,
    get_quiz_by_curriculum,
    get_quiz_attempts_by_user,
    insert_daily_log,
    update_lesson_sent,
    update_quiz_sent
)

load_dotenv()

def get_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment!")
    return Bot(token=token)

today = date.today()


async def send_daily_lesson():
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
                (w for w in curriculum if not w["is_completed"]),
                None
            )

            if not current_week:
        
                await get_bot().send_message(
                    chat_id=telegram_id,
                    text=(
                        "🎉 Congratulations! You completed your entire curriculum!\n"
                        "Type /learn to start a new topic!"
                    )
                )
                continue

         
            resources = get_resources_by_user_and_week(
                user_id=user_id,
                week_number=current_week["week_number"]
            )

           
            message_lines = [
                f"🌅 Good Morning! Today's Lesson:\n",
                f"📅 Week {current_week['week_number']}: {current_week['module_title']}",
                f"📝 {current_week['module_desc']}\n",
                f"📚 Resources:\n"
            ]

            if resources:
                for r in resources:
                    if r["resource_type"] == "youtube":
                        icon = "🎥"
                    elif r["resource_type"] == "article":
                        icon = "📖"
                    else:
                        icon = "🎓"

                    message_lines.append(
                        f"{icon} {r['title']}\n"
                        f"   {r['url']}"
                    )
            else:
                message_lines.append("No resources found for this week.")

            message_lines.append(
                "\n⏰ Quiz time at 8 PM tonight!\n"
                "Good luck with today's learning! 💪"
            )

        
            await get_bot().send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines)
            )

           
            today = date.today()
            insert_daily_log(
                user_id=user_id,
                curriculum_id=current_week["id"],
                sent_date=today
            )
            update_lesson_sent(
                user_id=user_id,
                curriculum_id=current_week["id"],
                sent_date=today)
            
            print(f"✅ Lesson sent to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending lesson to {user['telegram_id']}: {str(e)}")
            continue



async def send_evening_quiz():
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
                (w for w in curriculum if not w["is_completed"]),
                None
            )

            if not current_week:
                continue

           
            questions = get_quiz_by_curriculum(current_week["id"])
            if not questions:
                await get_bot().send_message(
                    chat_id=telegram_id,
                    text="No quiz available for today. Keep studying! 📚"
                )
                continue

          
            message_lines = [
                f"🧠 Evening Quiz Time!\n",
                f"📅 Week {current_week['week_number']}: {current_week['module_title']}\n"
            ]

            for i, q in enumerate(questions):
                message_lines.append(f"Q{i+1}: {q['question']}")
                message_lines.append(f"A) {q['option_a']}")
                message_lines.append(f"B) {q['option_b']}")
                message_lines.append(f"C) {q['option_c']}")
                message_lines.append(f"D) {q['option_d']}\n")

            message_lines.append("Reply with your answers like: A B C D A")

          
            await get_bot().send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines)
            )

          
            update_quiz_sent(
                user_id=user_id,
                curriculum_id=current_week["id"],
                sent_date=today
                )

           
            user_stages[telegram_id] = {"stage": "quiz"}

            
            active_quizzes[telegram_id] = {
                "questions": questions,
                "curriculum_id": current_week["id"],
                "user_id": user_id
            }

            print(f"✅ Quiz sent to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending quiz to {user['telegram_id']}: {str(e)}")
            continue


async def send_weekly_report():
    print("📊 Sending weekly reports...")

    users = get_all_active_users()

    for user in users:
        try:
            telegram_id = user["telegram_id"]
            user_id = user["id"]

            
            curriculum = get_curriculum_by_user(user_id)
            attempts = get_quiz_attempts_by_user(user_id)

            if not curriculum:
                continue

            
            completed = [w for w in curriculum if w["is_completed"]]
            total_weeks = len(curriculum)
            completed_weeks = len(completed)

           
            filled = int((completed_weeks / total_weeks) * 10)
            bar = "█" * filled + "░" * (10 - filled)

           
            if attempts:
                avg_score = sum(
                    (a["score"] / a["total"]) * 100
                    for a in attempts
                ) / len(attempts)
            else:
                avg_score = 0

            
            next_week = next(
                (w for w in curriculum if not w["is_completed"]),
                None
            )

            
            message_lines = [
                f"📊 Weekly Progress Report\n",
                f"👤 Topic: {user['topic']}",
                f"🎯 Level: {user['skill_level'].capitalize()}\n",
                f"Progress: [{bar}] {completed_weeks}/{total_weeks} weeks\n",
                f"📝 Quiz Average: {avg_score:.0f}%\n",
                f"✅ Completed Modules:"
            ]

            for week in curriculum:
                status = "✅" if week["is_completed"] else "⏳"
                message_lines.append(
                    f"  {status} Week {week['week_number']}: {week['module_title']}"
                )

            if next_week:
                message_lines.append(
                    f"\n📌 Next Week: {next_week['module_title']}"
                    f"\nKeep going! You're doing great! 🚀"
                )
            else:
                message_lines.append(
                    "\n🎉 You completed everything! Type /learn for a new topic!"
                )

            await get_bot().send_message(
                chat_id=telegram_id,
                text="\n".join(message_lines)
            )

            print(f"✅ Report sent to user {telegram_id}")

        except Exception as e:
            print(f"❌ Error sending report to {user['telegram_id']}: {str(e)}")
            continue
from datetime import datetime, timedelta

def setup_scheduler():
    scheduler = AsyncIOScheduler()

    # Run the lesson function 10 seconds from right now to test database insertion
    scheduler.add_job(
    send_daily_lesson,
    "date",
    run_date=datetime.now() + timedelta(seconds=10),
    id="test_immediate_log")

    
    #scheduler.add_job(
    # send_daily_lesson,
        #CronTrigger(hour=9, minute=0),
        #id="daily_lesson",
        #name="Send Daily Lesson",
        #replace_existing=True)

    
    #scheduler.add_job(
        #send_evening_quiz,
        #CronTrigger(hour=20, minute=0),
        #id="evening_quiz",
        #name="Send Evening Quiz",
        #replace_existing=True)

    scheduler.add_job(
    send_evening_quiz,
    "quiz",
    run_date=datetime.now() + timedelta(seconds=20),
    id="test_immediate_log")

    scheduler.add_job(
    send_weekly_report,
    "report",
    run_date=datetime.now() + timedelta(seconds=30),
    id="test_immediate_log")

    
    #scheduler.add_job(
        #send_weekly_report,
        #CronTrigger(day_of_week="sun", hour=10, minute=0),
        #id="weekly_report",
        #name="Send Weekly Report",
        #replace_existing=True)

    scheduler.start()
    print("⏰ Scheduler started!")
    print("  📚 Daily lesson  → 9:00 AM")
    print("  🧠 Evening quiz  → 8:00 PM")
    print("  📊 Weekly report → Sunday 10:00 AM")

    return scheduler