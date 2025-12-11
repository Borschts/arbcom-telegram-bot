import sqlite3
import contextlib

DB_NAME = "bot_database.db"

@contextlib.contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Motions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                creator_id INTEGER NOT NULL,
                creator_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                chat_id INTEGER NOT NULL
            )
        ''')
        
        # Votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                motion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                vote_type TEXT NOT NULL,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (motion_id) REFERENCES motions (id),
                UNIQUE(motion_id, user_id)
            )
        ''')
        
        # Arbitrators table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS arbitrators (
                user_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # System Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully.")

def add_arbitrator_db(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO arbitrators (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def remove_arbitrator_db(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM arbitrators WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_arbitrators_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM arbitrators")
        return [row['user_id'] for row in cursor.fetchall()]

# System Settings functions
def set_setting_db(key, value):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

def get_setting_db(key, default=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

# Motion related functions
def create_motion_db(title, content, creator_id, creator_username, chat_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO motions (title, content, creator_id, creator_username, chat_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, creator_id, creator_username, chat_id))
        conn.commit()
        return cursor.lastrowid

def get_active_motions_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM motions WHERE status = 'active'")
        return cursor.fetchall()

def get_motion_db(motion_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM motions WHERE id = ?", (motion_id,))
        return cursor.fetchone()

def close_motion_db(motion_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE motions SET status = 'closed' WHERE id = ?", (motion_id,))
        conn.commit()
        return cursor.rowcount > 0

# Vote related functions
def record_vote_db(motion_id, user_id, username, vote_type):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Use REPLACE to update existing vote or insert new one
        cursor.execute('''
            INSERT OR REPLACE INTO votes (motion_id, user_id, username, vote_type)
            VALUES (?, ?, ?, ?)
        ''', (motion_id, user_id, username, vote_type))
        conn.commit()

def get_motion_votes_db(motion_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM votes WHERE motion_id = ?", (motion_id,))
        return cursor.fetchall()

if __name__ == "__main__":
    init_db()
