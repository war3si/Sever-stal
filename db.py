import sqlite3
import json

DB_FILE = 'db.sqlite'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Важно: никаких # внутри SQL!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            points INTEGER DEFAULT 0,
            rewards TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

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
    cursor.execute('INSERT INTO users (id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def update_points(user_id, points_to_add):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (points_to_add, user_id))
    conn.commit()
    conn.close()

def add_reward(user_id, reward):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT rewards FROM users WHERE id = ?', (user_id,))
    rewards = json.loads(cursor.fetchone()[0])
    if reward not in rewards:
        rewards.append(reward)
    cursor.execute('UPDATE users SET rewards = ? WHERE id = ?', (json.dumps(rewards), user_id))
    conn.commit()
    conn.close()

def get_profile(user_id):
    user = get_user(user_id)
    if user:
        rewards = json.loads(user[3])
        return {
            'username': user[1],
            'points': user[2],
            'rewards': rewards
        }
    return None
