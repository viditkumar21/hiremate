import sqlite3
import json
from datetime import datetime, timezone

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            mastery TEXT,
            curiosity TEXT,
            chat_summary TEXT,
            last_topics TEXT,
            turn_count INTEGER,
            last_updated TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id: str) -> dict | None:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
        
    user_dict = dict(row)
    
    # Parse JSON fields
    json_fields = ["mastery", "curiosity", "last_topics"]
    for field in json_fields:
        if user_dict.get(field):
            try:
                user_dict[field] = json.loads(user_dict[field])
            except json.JSONDecodeError:
                pass # Already structured or string fallback
                
    return user_dict

def create_user(user_id: str) -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, mastery, curiosity, chat_summary, last_topics, turn_count, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, "{}", "{}", "", "{}", 0, now))
    
    conn.commit()
    conn.close()

def update_user(user_id: str, data: dict) -> None:
    if not data:
        return
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    set_clauses = []
    values = []
    
    json_fields = {"mastery", "curiosity", "last_topics"}
    
    for key, value in data.items():
        if key in ["user_id", "last_updated"]: # skip auto/primary key
            continue
            
        set_clauses.append(f"{key} = ?")
        
        if key in json_fields and isinstance(value, dict):
            values.append(json.dumps(value))
        else:
            values.append(value)
            
    if not set_clauses:
        conn.close()
        return
        
    set_clauses.append("last_updated = ?")
    values.append(datetime.now(timezone.utc).isoformat())
    values.append(user_id)
    
    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?"
    cursor.execute(query, values)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    
    create_user("test_user")
    print("Created 'test_user'.")
    
    print("\nFetching 'test_user'...")
    user = get_user("test_user")
    print(user)
    
    print("\nUpdating 'test_user' with mastery...")
    update_user("test_user", {"mastery": {"math": 80}})
    
    print("Fetching 'test_user' again...")
    user2 = get_user("test_user")
    print(user2)
