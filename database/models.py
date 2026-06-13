from database.connection import get_connection

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                telegram_id   BIGINT UNIQUE NOT NULL,
                username      VARCHAR(100),
                topic         VARCHAR(200),
                skill_level   ENUM('beginner','intermediate','advanced'),
                is_active     BOOLEAN DEFAULT TRUE,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS curriculums (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                user_id       INT,
                week_number   INT,
                module_title  VARCHAR(200),
                module_desc   TEXT,
                is_completed  BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                curriculum_id INT,
                title         VARCHAR(300),
                url           TEXT,
                resource_type ENUM('youtube','article','course','docs'),
                FOREIGN KEY (curriculum_id) REFERENCES curriculums(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                curriculum_id INT,
                question      TEXT,
                option_a      VARCHAR(300),
                option_b      VARCHAR(300),
                option_c      VARCHAR(300),
                option_d      VARCHAR(300),
                correct_ans   ENUM('A','B','C','D'),
                FOREIGN KEY (curriculum_id) REFERENCES curriculums(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                user_id       INT,
                curriculum_id INT,
                score         INT,
                total         INT,
                attempted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (curriculum_id) REFERENCES curriculums(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_logs (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                user_id       INT,
                curriculum_id INT,
                lesson_sent   BOOLEAN DEFAULT FALSE,
                quiz_sent     BOOLEAN DEFAULT FALSE,
                sent_date     DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        print("All tables created successfully!")

    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()