import sqlite3
import os
from typing import FrozenSet, Set, Tuple

DB_FILE = 'mensabot.db'

# Database setup
def add_schedule_to_db(chat_id: str,
                       location_id: str,
                       time_str: str = "10:00",
                       days_of_week: str = 'DAILY'):
    """Add a schedule to the database."""
    try:
        conn = create_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (chat_id, location_id, time, days_of_week)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, location_id, time_str, days_of_week))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while adding a schedule: {e}")
        raise Exception(f"Failed to add schedule to database: {e}")
    finally:
        cursor.close()

def remove_schedule_from_db(chat_id: str, location_id: str,
                            time_str: str, days_of_week: str):
    """Remove a schedule from the database."""
    try:
        conn = create_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM messages
            WHERE chat_id = ? AND location_id = ? AND time = ? AND days_of_week = ?
        ''', (chat_id, location_id, time_str, days_of_week))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while removing a schedule: {e}")
        raise Exception(f"Failed to remove schedule from database: {e}")
    finally:
        cursor.close()

def retrieve_schedules() -> Set[Tuple[str, str, str, str]]:
    """Retrieve all schedules from the database."""
    try:
        conn = create_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages')
        rows = cursor.fetchall()
        schedules = []
        for row in rows:
            schedule = (row[1], row[2], row[3], row[4])
              # chat_id, location_id, time, days_of_week
            schedules.append(schedule)  # Convert to frozenset for immutability
        return set(schedules)  # Return as a set for uniqueness
    except sqlite3.Error as e:
        print(f"An error occurred while retrieving schedules: {e}")
        return set()
    finally:
        cursor.close()

def create_table(conn: sqlite3.Connection):
    """Create a table in the database if it does not exist."""
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                location_id TEXT NOT NULL,
                time TEXT DEFAULT '10:00',
                days_of_week TEXT NOT NULL DEFAULT 'mon-fri'
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while creating the table: {e}")
    finally:
        cursor.close()

def create_connection(db_file: str) -> sqlite3.Connection:
    """Create a database connection to the SQLite database specified by db_file."""
    if not db_file:
        raise ValueError("Database file path must be provided.")
    if not os.path.exists(db_file):
        # create the file
        with open(db_file, 'w'):
            pass
    conn = sqlite3.connect(db_file)
    # Just in case we run the create_table command
    create_table(conn)
    return conn
