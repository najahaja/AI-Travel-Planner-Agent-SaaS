import sqlite3
import os

DB_PATH = "travel_planner.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if session_id exists in travel_plans
        cursor.execute("PRAGMA table_info(travel_plans)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "session_id" not in columns:
            print("Adding session_id column to travel_plans table...")
            cursor.execute("ALTER TABLE travel_plans ADD COLUMN session_id INTEGER REFERENCES chat_sessions(id) ON DELETE SET NULL")
            print("session_id column added successfully.")
        else:
            print("session_id column already exists in travel_plans.")

        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
