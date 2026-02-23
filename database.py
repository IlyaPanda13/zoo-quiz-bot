import sqlite3
from contextlib import closing
import logging
import json

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='quiz_bot.db'):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Инициализация базы данных"""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    current_question INTEGER DEFAULT 1,
                    scores TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для отзывов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    feedback_text TEXT,
                    animal_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.commit()

    def add_user(self, user_id, username, first_name):
        """Добавление нового пользователя"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name)
                    VALUES (?, ?, ?)
                ''', (user_id, username, first_name))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")

    def get_user_state(self, user_id):
        """Получение состояния пользователя"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT current_question, scores FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()

                if result:
                    current_question, scores_json = result
                    scores = json.loads(scores_json) if scores_json else {}
                    return current_question, scores
                return 1, {}
        except Exception as e:
            logger.error(f"Ошибка при получении состояния: {e}")
            return 1, {}

    def update_user_state(self, user_id, current_question, scores):
        """Обновление состояния пользователя"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                scores_json = json.dumps(scores)

                cursor.execute('''
                    UPDATE users 
                    SET current_question = ?, scores = ?
                    WHERE user_id = ?
                ''', (current_question, scores_json, user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении состояния: {e}")

    def reset_user(self, user_id):
        """Сброс состояния пользователя для начала новой викторины"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET current_question = 1, scores = '{}'
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при сбросе пользователя: {e}")

    def save_feedback(self, user_id, username, feedback_text, animal_result):
        """Сохранение отзыва в базу"""
        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO feedback (user_id, username, feedback_text, animal_result)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, feedback_text, animal_result))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении отзыва: {e}")
            return False


def clean_old_data(self, days=30):
    """Удаление данных пользователей старше N дней"""
    try:
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()

            # Оставляем только результаты викторин за последние 30 дней
            cursor.execute('''
                DELETE FROM users 
                WHERE created_at < datetime('now', ?)
            ''', (f'-{days} days',))

            # Оставляем отзывы за последние 30 дней
            cursor.execute('''
                DELETE FROM feedback 
                WHERE created_at < datetime('now', ?)
            ''', (f'-{days} days',))

            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка при очистке данных: {e}")
        return False

db = Database()