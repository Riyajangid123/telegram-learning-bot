import json
from database.connection import get_connection

def create_user(telegram_id, username):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users(telegram_id, username)
    VALUES(%s,%s)
    ON CONFLICT (telegram_id)
    DO NOTHING
    """,(telegram_id,username))

    conn.commit()

    cur.close()
    conn.close()

def get_user(telegram_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM users
    WHERE telegram_id=%s
    """,(telegram_id,))

    user=cur.fetchone()

    cur.close()
    conn.close()

    return user

def create_learning_topic(user_id,topic):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO learning_topics(user_id,topic)
    VALUES(%s,%s)
    RETURNING id
    """,(user_id,topic))

    topic_id=cur.fetchone()[0]

    conn.commit()

    cur.close()
    conn.close()

    return topic_id

def get_latest_topic(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT id,topic
    FROM learning_topics
    WHERE user_id=%s
    ORDER BY id DESC
    LIMIT 1
    """,(user_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

def save_skill_assessment(topic_id,assessment):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO skill_assessments(topic_id,assessment)
    VALUES(%s,%s)
    """,
    (
        topic_id,
        json.dumps(assessment)
    ))

    conn.commit()

    cur.close()
    conn.close()

def get_latest_skill_assessment(topic_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT assessment
    FROM skill_assessments
    WHERE topic_id=%s
    ORDER BY id DESC
    LIMIT 1
    """,(topic_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

def save_curriculum(topic_id,curriculum):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO curriculums(topic_id,curriculum)
    VALUES(%s,%s)
    RETURNING id
    """,
    (
        topic_id,
        json.dumps(curriculum)
    ))

    curriculum_id=cur.fetchone()[0]

    conn.commit()

    cur.close()
    conn.close()

    return curriculum_id

def get_curriculum(curriculum_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT curriculum
    FROM curriculums
    WHERE id=%s
    """,(curriculum_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

def save_resources(curriculum_id,resources):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO resources(curriculum_id,resources)
    VALUES(%s,%s)
    """,
    (
        curriculum_id,
        json.dumps(resources)
    ))

    conn.commit()

    cur.close()
    conn.close()

def save_quiz(curriculum_id,quiz):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO quizzes(curriculum_id,quiz)
    VALUES(%s,%s)
    RETURNING id
    """,
    (
        curriculum_id,
        json.dumps(quiz)
    ))

    quiz_id=cur.fetchone()[0]

    conn.commit()

    cur.close()
    conn.close()

    return quiz_id

def get_latest_quiz(curriculum_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT id,quiz
    FROM quizzes
    WHERE curriculum_id=%s
    ORDER BY id DESC
    LIMIT 1
    """,(curriculum_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

def save_quiz_attempt(
        quiz_id,
        user_id,
        answers,
        evaluation,
        score
):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO quiz_attempts(
        quiz_id,
        user_id,
        answers,
        evaluation,
        score
    )
    VALUES(%s,%s,%s,%s,%s)
    """,
    (
        quiz_id,
        user_id,
        json.dumps(answers),
        json.dumps(evaluation),
        score
    ))

    conn.commit()

    cur.close()
    conn.close()

def get_quiz_history(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT *
    FROM quiz_attempts
    WHERE user_id=%s
    ORDER BY attempted_at DESC
    """,(user_id,))

    rows=cur.fetchall()

    cur.close()
    conn.close()

    return rows

def save_progress(
        user_id,
        topic_id,
        report
):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO progress_reports(
        user_id,
        topic_id,
        report
    )
    VALUES(%s,%s,%s)
    """,
    (
        user_id,
        topic_id,
        json.dumps(report)
    ))

    conn.commit()

    cur.close()
    conn.close()

def get_latest_progress(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT report
    FROM progress_reports
    WHERE user_id=%s
    ORDER BY id DESC
    LIMIT 1
    """,(user_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

def update_session(user_id,phase,topic_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO sessions(
        user_id,
        current_phase,
        current_topic_id
    )
    VALUES(%s,%s,%s)

    ON CONFLICT(user_id)

    DO UPDATE SET

    current_phase=EXCLUDED.current_phase,
    current_topic_id=EXCLUDED.current_topic_id,
    updated_at=CURRENT_TIMESTAMP
    """,
    (
        user_id,
        phase,
        topic_id
    ))

    conn.commit()

    cur.close()
    conn.close()

def get_session(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT current_phase,current_topic_id
    FROM sessions
    WHERE user_id=%s
    """,(user_id,))

    row=cur.fetchone()

    cur.close()
    conn.close()

    return row

