import sqlite3
import os
import sys

def enable_wal():
    try:
        # __file__ is inside backend/tests/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # go up to backend/
        backend_dir = os.path.dirname(current_dir)
        db_path = os.path.join(backend_dir, 'data', 'bus_data.db')
        
        print(f"Connecting to database at: {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current mode
        cursor.execute("PRAGMA journal_mode;")
        current_mode = cursor.fetchone()[0]
        print(f"Current journal mode: {current_mode}")
        
        # Set WAL mode
        cursor.execute("PRAGMA journal_mode=WAL;")
        new_mode = cursor.fetchone()[0]
        print(f"New journal mode: {new_mode}")
        
        conn.close()
        
        if new_mode.upper() == 'WAL':
            print("Successfully enabled WAL mode.")
        else:
            print("Failed to enable WAL mode.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enable_wal()
