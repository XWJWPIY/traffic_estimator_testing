import sqlite3
import os
import sys

# Ensure backend/functions is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'functions'))

def check_route(route_name):
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'bus_data.db')
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"--- Searching for Route: {route_name} ---")
    cursor.execute('SELECT id, route_unique_id, nameZh, city FROM routes WHERE nameZh = ?', (route_name,))
    rows = cursor.fetchall()
    
    if not rows:
        print("No routes found.")
    
    for row in rows:
        r_pk, r_uid, r_name, r_city = row
        print(f"Route PK:{r_pk}, UniqueID:{r_uid}, Name:{r_name}, City:{r_city}")
        
        # Check stops
        cursor.execute("SELECT COUNT(*) FROM stops WHERE route_unique_id = ?", (r_uid,))
        stop_count = cursor.fetchone()[0]
        print(f"  -> Stop Count: {stop_count}")
        
        if stop_count == 0:
            print("  -> WARNING: No stops found for this Route Unique ID.")

    conn.close()


def check_route_buffer(name_zh):
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'bus_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"--- Checking Buffer for Route {name_zh} ---")
    cursor.execute("SELECT route_unique_id, segmentBufferZh, ticketPriceDescriptionZh FROM routes WHERE nameZh = ?", (name_zh,))
    row = cursor.fetchone()
    if row:
        rid = row[0]
        print(f"ID: {rid}")
        print(f"SegmentBufferZh: {row[1]!r}")
        print(f"TicketPriceDescriptionZh: {row[2]!r}")
        
        # Check route_fares table
        print(f"--- Checking route_fares table for RouteID {rid} ---")
        cursor.execute("SELECT direction, section_sequence, origin_stop_id, destination_stop_id, description FROM route_fares WHERE route_unique_id = ?", (rid,))
        fares = cursor.fetchall()
        for f in fares:
             print(f"  Fare: Dir{f[0]}, Seq{f[1]}, Origin{f[2]}->Dest{f[3]}, Desc:{f[4]}")
        
    else:
        print("Route not found.")
    
    # List all stops for this route to check names
    if row:
        print("--- Stop List ---")
        cursor.execute("SELECT seqNo, nameZh FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (row[0],))
        stops = cursor.fetchall()
        for s in stops:
            if '格致' in s[1] or '正義' in s[1]:
                print(f"  Seq {s[0]}: {s[1]!r}")
    
    conn.close()

if __name__ == "__main__":
    check_route_buffer("232快")
