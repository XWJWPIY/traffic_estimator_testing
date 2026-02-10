import sqlite3
import os
import sys
import traceback

# Import backend logic
try:
    # __file__ is in backend/tests/
    # Go up to backend/
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    functions_dir = os.path.join(backend_dir, 'functions')
    sys.path.append(functions_dir)
    
    # IMPORT process_hybrid_route
    from parse_buffer_zones import parse_buffer_text, compute_buffer_events, clean_name, process_hybrid_route
    import parse_buffer_zones # Need module for some calls
except Exception:
    traceback.print_exc()
    sys.exit(1)

# Set encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def debug_route(route_name_zh, print_all_stops=False):
    print(f"\n{'='*60}")
    print(f"DEBUG REPORT FOR ROUTE: {route_name_zh}")
    print(f"{'='*60}")
    
    # DB path relative to script location
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, 'data', 'bus_data.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Get Route Info
    c.execute("SELECT * FROM routes WHERE nameZh = ?", (route_name_zh,))
    route = c.fetchone()
    if not route:
        print(f"!! Route '{route_name_zh}' not found in DB.")
        conn.close()
        return

    rid = route['route_unique_id']
    buffer_text = route['segmentBufferZh']
    ticket_desc = route['ticketPriceDescriptionZh']
    
    print(f"Route ID: {rid}")
    print(f"Raw Buffer Text: {buffer_text}")
    print(f"Ticket Desc: {ticket_desc}")
    
    # 2. RUN REAL-WORLD LOGIC (Hybrid)
    print("\n--- Running Hybrid Process (Production Logic) ---")
    
    # We want to Capture the events, not just write them to DB.
    # But process_hybrid_route writes to DB directly.
    # For debugging, we can manually replicate process_hybrid_route steps OR inspect the DB after running it.
    # To be safe and show clear steps, let's replicate the steps but using the shared function logic manually
    # OR we can just modify process_hybrid_route to return events, but I shouldn't change backend code just for test.
    # Actually, process_hybrid_route returns "True" on success.
    # Let's run it to update the in-memory DB (or temp DB) and then read the results?
    # No, verify_routes_template usually just computes events.
    
    # Better approach: Mimic process_hybrid_route's decision flow here to show WHAT happened.
    
    # Step A: Try Text
    ranges = None
    source = "None"
    if buffer_text and buffer_text.strip():
        ranges = parse_buffer_text(buffer_text)
        if ranges: source = "Text Buffer"
        
    # Step B: Try Structured
    manual_zones = []
    if not ranges:
        from parse_buffer_zones import fetch_structured_zones
        # Fetch stops for this part
        c.execute("SELECT * FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (rid,))
        stops_for_struct = c.fetchall()
        
        manual_zones = fetch_structured_zones(c, rid, stops_for_struct)
        if manual_zones:
            source = "Structured Data (DB)"
        else:
            # Step C: Try Ticket Desc
            if ticket_desc:
                ranges = parse_buffer_text(ticket_desc)
                if ranges: source = "Ticket Description"
                
    print(f"Selected Source: {source}")
    if ranges:
        for i, r in enumerate(ranges):
            start, end, direction = r
            dir_str = "Both" if direction is None else ("Go (0)" if direction == 0 else "Back (1)")
            print(f"  Range {i+1}: {start} -> {end} [{dir_str}]")
    if manual_zones:
         print(f"  Found {len(manual_zones)} structured zones from DB.")

    # 3. Fetch Stops
    c.execute("SELECT * FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (rid,))
    stops = c.fetchall()
    
    if print_all_stops:
        print("\n--- Stop List ---")
        for s in stops:
            print(f"  Seq {s['seqNo']}: {s['nameZh']} (Dir: {s['goBack']})")
    
    # 4. Compute Events
    print("\n--- Computed Events ---")
    events = compute_buffer_events(stops, ranges=ranges, route_name=route_name_zh, manual_zones=manual_zones)
    
    # 5. Display Result
    go_stops = [s for s in stops if s['goBack'] == 0]
    back_stops = [s for s in stops if s['goBack'] == 1]
    
    def print_events(stop_list, label):
        print(f"\n[{label} Direction]")
        for s in stop_list:
            seq = s['seqNo']
            evs = events.get(seq, [])
            
            # Count events to show stacking (e.g. [START x5])
            ev_str = ""
            
            # Map keys to display labels
            target_events = [
                ('start', '[START]'),
                ('end', '[END]'),
                ('end_of_go', '[END OF GO]'),
                ('start_of_back', '[START OF BACK]'),
                ('start_of_loop', '[START OF LOOP]'),
                ('end_of_loop', '[END OF LOOP]')
            ]
            
            for key, label_text in target_events:
                count = evs.count(key)
                if count == 1:
                    ev_str += f"{label_text} "
                elif count > 1:
                    # Insert xN inside the bracket, e.g. [START x5]
                    # Assume label_text is like [START] -> [START xN]
                    base_label = label_text[0:-1] # remove ']'
                    ev_str += f"{base_label} x{count}] "
            
            if ev_str:
                print(f"  Seq {seq:3d}: {s['nameZh']:<15} {ev_str}")
        
    print_events(go_stops, "Outbound (Go)")
    print_events(back_stops, "Inbound (Back)")
    
    conn.close()

if __name__ == "__main__":
    # ==========================================
    # TEST CASES - Add Routes Here
    # ==========================================
    
    # 未經虛擬站測資

    # 二段票
    debug_route("承德幹線")
    debug_route("中山幹線")
    debug_route("忠孝幹線")
    debug_route("北環幹線")
    debug_route("202")
    debug_route("202區")
    debug_route("214")
    debug_route("222")
    debug_route("226")
    debug_route("212直")
    debug_route("262區")
    debug_route("299")
    debug_route("307")
    debug_route("311")
    debug_route("906")
    debug_route("950")
    debug_route("957")
    debug_route("綠13")
    debug_route("670")
    
    # 三段票
    debug_route("706")
    debug_route("711")
    debug_route("857")
    debug_route("304承德")
    debug_route("304重慶")
    
    # 四段票以上
    debug_route("862")

    # 迴轉處內部緩衝區型
    debug_route("254")
    debug_route("672")

    # 跨越迴轉處緩衝區型
    debug_route("249")
    debug_route("221")

    # 特殊終點設計
    debug_route("262") # 去返程斷開

    debug_route("2")
    debug_route("232快")
    debug_route("819副")

    debug_route("22")
    debug_route("705")
    debug_route("1")
    debug_route("37")
    debug_route("內科通勤專車21")

    debug_route("908")
    debug_route("953")
    debug_route("953區")
    debug_route("965(台灣好行-九份金瓜石線)")

    debug_route("966")
    debug_route("232")
    debug_route("232快")

    debug_route("849")
    debug_route("849屈尺社區")