import os
from database.connection import get_connection
from psycopg2.extras import RealDictCursor

def insert_user(telegram_id, username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, username)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
        """, (telegram_id, username))
        conn.commit()
        print(f"User {username} handled.")
    except Exception as e:
        print(f"Insert user error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_user_by_telegram_id(telegram_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cursor.fetchone()
        print(f"DEBUG raw result: {user}")
        return user
    finally:
        cursor.close()
        conn.close()
    
def update_user_topic_skill_level(telegram_id, topic, skill_level):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET topic = %s, skill_level = %s 
            WHERE telegram_id = %s
        """, (topic, skill_level, telegram_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_curriculum(user_id, curriculum: list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for week in curriculum:
            cursor.execute("""
                INSERT INTO curriculums(user_id, week_number, module_title, module_desc) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, week["week"], week["title"], week["description"]))
        conn.commit()
        print(f"Curriculum inserted for user {user_id}")
    except Exception as e:
        print(f"Insert curriculum error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_curriculum_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
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
            WHERE user_id = %s AND week_number = %s
        """, (user_id, week_number))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_resources(curriculum_id, resources: list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for resource in resources:
            cursor.execute("""
                INSERT INTO resources (curriculum_id, title, url, resource_type)
                VALUES (%s, %s, %s, %s)
            """, (curriculum_id, resource["title"], resource["url"], resource["type"]))
        conn.commit()
    except Exception as e:
        print(f"Insert resources error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_resources_by_user_and_week(user_id, week_number):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT r.* FROM resources r
            JOIN curriculums c ON r.curriculum_id = c.id
            WHERE c.user_id = %s AND c.week_number = %s
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
                INSERT INTO quizzes (curriculum_id, question, option_a, option_b, option_c, option_d, correct_ans)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (curriculum_id, q["question"], q["options"]["A"], q["options"]["B"], q["options"]["C"], q["options"]["D"], q["correct"]))
        conn.commit()
    except Exception as e:
        print(f"Insert quiz error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_quiz_by_curriculum(curriculum_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM quizzes WHERE curriculum_id = %s", (curriculum_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def insert_quiz_attempt(user_id, curriculum_id, score, total):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO quiz_attempts (user_id, curriculum_id, score, total)
            VALUES (%s, %s, %s, %s)
        """, (user_id, curriculum_id, score, total))
        conn.commit()
    except Exception as e:
        print(f"Insert quiz attempt error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

def get_quiz_attempts_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT qa.*, c.week_number, c.module_title
            FROM quiz_attempts qa
            JOIN curriculums c ON qa.curriculum_id = c.id
            WHERE qa.user_id = %s
            ORDER BY qa.attempted_at DESC
        """, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_all_active_users():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM users WHERE is_active = TRUE")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()