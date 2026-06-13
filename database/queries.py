from graph.state import LearningState
from database.connection import get_connection

def insert_user(telegram_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, username)
            VALUES (%s, %s)
        """, (telegram_id, username))
        conn.commit()
        print(f"User {username} inserted")
    except Exception as e:
        print(f"Insert user error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_user_by_telegram_id(telegram_id):
    conn=get_connection()
    cursor=conn.cursor(dictionary=True)

    cursor.execute("""
                   select * from users where
                   telegram_id=%s""",
                   (telegram_id,))
    
    user=cursor.fetchone()
    print(f"DEBUG raw result: {user}")
    conn.close()

    if user:
        return user
    else:
        return None
    
def update_user_topic_skill_level(telegram_id,topic,skill_level):
    conn=get_connection()
    cursor=conn.cursor()
    try:
        cursor.execute("""
                    update users set topic=%s,
                    skill_level=%s where telegram_id=%s""",
                    (topic,
                        skill_level,
                        telegram_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_curriculum(user_id,curriculum:list):
    conn=get_connection()
    cursor=conn.cursor()

    try:
        for week in curriculum:
            cursor.execute("""insert into curriculums(user_id, week_number, module_title, module_desc) 
                        values(%s,%s,%s,%s)""",
                        (user_id,
                        week["week"],
                        week["title"],
                        week["description"]))
        conn.commit()

        print(f"Curriculum inserted for user {user_id}")
    except Exception as e:
        print(f"Insert curriculum error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_curriculum_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM curriculums
            WHERE user_id = %s
            ORDER BY week_number
        """, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def mark_module_completed(user_id, week_number):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE curriculums
            SET is_completed = TRUE
            WHERE user_id = %s
            AND week_number = %s
        """, (user_id, week_number))
        conn.commit()
        print(f"Week {week_number} marked complete")
    finally:
        cursor.close()
        conn.close()

def insert_resources(curriculum_id, resources: list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for resource in resources:
            cursor.execute("""
                INSERT INTO resources 
                    (curriculum_id, title, url, resource_type)
                VALUES (%s, %s, %s, %s)
            """, (
                curriculum_id,
                resource["title"],
                resource["url"],
                resource["type"]   
            ))
        conn.commit()
        print(f"Resources inserted for curriculum {curriculum_id}")
    except Exception as e:
        print(f"Insert resources error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_resources_by_curriculum(curriculum_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM resources
            WHERE curriculum_id = %s
        """, (curriculum_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_resources_by_user_and_week(user_id, week_number):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.* 
            FROM resources r
            JOIN curriculums c ON r.curriculum_id = c.id
            WHERE c.user_id = %s
            AND c.week_number = %s
        """, (user_id, week_number))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def insert_quiz_questions(curriculum_id, questions: list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for q in questions:
            cursor.execute("""
                INSERT INTO quizzes
                    (curriculum_id, question, 
                     option_a, option_b, option_c, option_d,
                     correct_ans)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                curriculum_id,
                q["question"],
                q["options"]["A"],
                q["options"]["B"],
                q["options"]["C"],
                q["options"]["D"],
                q["correct"]
            ))
        conn.commit()
        print(f"Quiz questions inserted")
    except Exception as e:
        print(f"Insert quiz error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_quiz_by_curriculum(curriculum_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM quizzes
            WHERE curriculum_id = %s
        """, (curriculum_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def insert_quiz_attempt(user_id, curriculum_id, score, total):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO quiz_attempts
                (user_id, curriculum_id, score, total)
            VALUES (%s, %s, %s, %s)
        """, (user_id, curriculum_id, score, total))
        conn.commit()
        print(f"Quiz attempt saved: {score}/{total}")
    except Exception as e:
        print(f"Insert quiz attempt error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_quiz_attempts_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                qa.*,
                c.week_number,
                c.module_title
            FROM quiz_attempts qa
            JOIN curriculums c ON qa.curriculum_id = c.id
            WHERE qa.user_id = %s
            ORDER BY qa.attempted_at DESC
        """, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()



def insert_daily_log(user_id, curriculum_id, sent_date):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO daily_logs
                (user_id, curriculum_id, sent_date)
            VALUES (%s, %s, %s)
        """, (user_id, curriculum_id, sent_date))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_lesson_sent(user_id, sent_date):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE daily_logs
            SET lesson_sent = TRUE
            WHERE user_id = %s
            AND sent_date = %s
        """, (user_id, sent_date))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_quiz_sent(user_id, sent_date):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE daily_logs
            SET quiz_sent = TRUE
            WHERE user_id = %s
            AND sent_date = %s
        """, (user_id, sent_date))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_all_active_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM users
            WHERE is_active = TRUE
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


