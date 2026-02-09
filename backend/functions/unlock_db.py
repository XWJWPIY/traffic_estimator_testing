import os
import subprocess
import sqlite3
import time

def kill_parser_process():
    print("Searching for running parser processes...")
    try:
        # Check for python processes running parse_buffer_zones.py
        # This is a basic check using tasklist
        cmd = 'tasklist /FI "IMAGENAME eq python.exe" /V /FO CSV'
        output = subprocess.check_output(cmd, shell=True).decode('cp950', errors='ignore')
        
        lines = output.strip().split('\r\n')
        killed = False
        
        for line in lines:
            if "parse_buffer_zones.py" in line or "python" in line:
                # We can't easily see the script name in tasklist /V for python sometimes
                # So we will be aggressive if requested, but let's try to be smart.
                # Actually, standard tasklist doesn't show command line arguments well.
                pass
                
        # Simpler approach for Windows dev env:
        # Just tell user we are killing python processes that might be the parser
        print("Stopping any background python operations...")
        os.system("taskkill /F /FI \"WINDOWTITLE eq parse_buffer_zones.py*\"") # If launched with start
        
        # Or just generic kill of python if it's the only way, but that kills this script too.
        # We will try to just reset the DB lock. Usually stopping the writer is enough.
        
        # Let's try to acquire a lock. If we can't, we warn.
        print("Attempting to acquire DB lock...")
        
    except Exception as e:
        print(f"Error checking processes: {e}")

def force_reset_wal():
    # __file__ is in backend/functions/
    # backend is parent dir
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, 'data', 'bus_data.db')
    print(f"Target DB: {db_path}")
    
    try:
        # 1. Force Close existing connections? 
        # We can't from here, but we can try to switch modes which forces a checkpoint if possible.
        
        conn = sqlite3.connect(db_path, timeout=1)
        cursor = conn.cursor()
        
        print("Resetting Journal Mode to DELETE (Flush)...")
        cursor.execute("PRAGMA journal_mode=DELETE;")
        conn.commit()
        
        print("Setting Journal Mode back to WAL...")
        cursor.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        
        conn.close()
        print("✅ Database unlocked and WAL mode enabled successfully.")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Database is still locked by another process: {e}")
        print("You may need to manually kill the python process in Task Manager.")
        print("Running aggressive kill command for all python processes (except this one)...")
        
        # Aggressive kill - excluding self if possible, but hard in pure python without psutil
        # Just suggested command
        print("Run this in terminal to kill all python: taskkill /IM python.exe /F")

if __name__ == "__main__":
    # kill_parser_process() # Hard to do reliably without killing self
    force_reset_wal()
