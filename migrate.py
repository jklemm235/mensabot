import schedulerDB as db
import sqlite3

def migrate():
    conn = db.create_connection(db.DB_FILE)
        # This will also call the create_table function

    # Migration logic:
    # check if the day_to_report column exists
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'day_to_report' not in columns:
            # Add the new column
            cursor.execute("ALTER TABLE messages ADD COLUMN day_to_report TEXT DEFAULT 'today'")
            conn.commit()
            print("Migration successful: Added 'day_to_report' column to 'messages' table.")
        else:
            print("'day_to_report' column already exists. No migration needed.")
    except sqlite3.Error as e:
        print(f"An error occurred during migration: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
    print("Migration completed.")