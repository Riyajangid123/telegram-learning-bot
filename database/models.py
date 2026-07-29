from database.connection import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ==========================
        # USERS
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # LEARNING TOPICS
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_topics(
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic VARCHAR(255) NOT NULL,
            status VARCHAR(30) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # SKILL ASSESSMENTS
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_assessments(
            id SERIAL PRIMARY KEY,
            topic_id INT NOT NULL REFERENCES learning_topics(id) ON DELETE CASCADE,
            assessment JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # CURRICULUM
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS curriculums(
            id SERIAL PRIMARY KEY,
            topic_id INT NOT NULL REFERENCES learning_topics(id) ON DELETE CASCADE,
            curriculum JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # RESOURCES
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources(
            id SERIAL PRIMARY KEY,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            resources JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # QUIZZES
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes(
            id SERIAL PRIMARY KEY,
            curriculum_id INT NOT NULL REFERENCES curriculums(id) ON DELETE CASCADE,
            quiz JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # QUIZ ATTEMPTS
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts(
            id SERIAL PRIMARY KEY,
            quiz_id INT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            answers JSONB NOT NULL,
            evaluation JSONB NOT NULL,
            score FLOAT,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # PROGRESS REPORTS
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress_reports(
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic_id INT NOT NULL REFERENCES learning_topics(id) ON DELETE CASCADE,
            report JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # ==========================
        # USER SESSION
        # ==========================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id SERIAL PRIMARY KEY,
            user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            current_phase VARCHAR(100),
            current_topic_id INT REFERENCES learning_topics(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        print("✅ Tables created successfully.")

    except Exception as e:
        conn.rollback()
        print(e)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_tables()