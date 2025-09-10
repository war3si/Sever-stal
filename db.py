import sqlite3
import json

DB_FILE = "db.sqlite"  # Путь к базе данных

def init_db():
    print("LOG: Инициализация базы данных...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            rewards TEXT DEFAULT '[]',
            day1_completed INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN day1_completed INTEGER DEFAULT 0')
        print("LOG: Колонка 'day1_completed' успешно добавлена.")
    except sqlite3.OperationalError:
        # Колонка уже существует, это нормально
        pass
        
    conn.commit()
    conn.close()
    print("LOG: Инициализация БД завершена.")

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    if cursor.rowcount > 0:
        print(f"LOG WRITE: Создан пользователь с ID={user_id}, username='{username}'")
    else:
        print(f"LOG INFO: Пользователь с ID={user_id} уже существует.")
    conn.close()

def update_points(user_id, points_to_add):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (points_to_add, user_id))
    conn.commit()
    print(f"LOG WRITE: Пользователю ID={user_id} добавлено {points_to_add} очков.")
    conn.close()

def mark_day1_completed(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET day1_completed = 1 WHERE id = ?', (user_id,))
    conn.commit()
    print(f"LOG WRITE: Для пользователя ID={user_id} день 1 отмечен как пройденный.")
    conn.close()

def has_completed_day1(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT day1_completed FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def add_reward(user_id, reward):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT rewards FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    rewards = json.loads(row[0])
    if reward not in rewards:
        rewards.append(reward)
    cursor.execute('UPDATE users SET rewards = ? WHERE id = ?', (json.dumps(rewards), user_id))
    conn.commit()
    print(f"LOG WRITE: Пользователю ID={user_id} добавлена награда '{reward}'.")
    conn.close()

def get_profile(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, points, rewards FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        return None
    rewards = json.loads(user[3]) if user[3] else []
    return {
        "id": user[0],
        "username": user[1],
        "points": user[2],
        "rewards": rewards
    }