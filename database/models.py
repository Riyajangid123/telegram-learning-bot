from database.connection import get_connection

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    try:

        # USERS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            topic VARCHAR(200),
            skill_level VARCHAR(50)
                CHECK (skill_level IN ('beginner','intermediate','advanced')),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # CURRICULUMS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS curriculums (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            week_number INT NOT NULL,
            module_title VARCHAR(200) NOT NULL,
            module_desc TEXT,
            is_completed BOOLEAN DEFAULT FALSE
        );
        """)

        # RESOURCES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id SERIAL PRIMARY KEY,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            title VARCHAR(300) NOT NULL,
            url TEXT NOT NULL,
            resource_type VARCHAR(50)
                CHECK (resource_type IN ('youtube','article','course','docs'))
        );
        """)

        # QUIZZES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id SERIAL PRIMARY KEY,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            option_a VARCHAR(300) NOT NULL,
            option_b VARCHAR(300) NOT NULL,
            option_c VARCHAR(300) NOT NULL,
            option_d VARCHAR(300) NOT NULL,
            correct_ans VARCHAR(5)
                CHECK (correct_ans IN ('A','B','C','D'))
        );
        """)

        # QUIZ ATTEMPTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            score INT NOT NULL,
            total INT NOT NULL,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # DAILY LOG
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            lesson_sent BOOLEAN DEFAULT FALSE,
            quiz_sent BOOLEAN DEFAULT FALSE,
            sent_date DATE NOT NULL,
            UNIQUE(user_id, curriculum_id, sent_date)
        );
        """)

        conn.commit()
        print("✅ All tables created successfully.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating tables: {e}")

    finally:
        cursor.close()
        conn.close()