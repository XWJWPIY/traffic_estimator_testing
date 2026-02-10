import sqlite3
import sys
import os
import re

# Add parent directory to path to import db conversion if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def parse_buffer_zones_from_db():
    try:
        db_path = os.path.join(os.path.dirname(__file__), '../data/bus_data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Enable WAL mode for concurrency
        c.execute("PRAGMA journal_mode=WAL")
        
        # Get all routes
        c.execute("SELECT route_unique_id, nameZh, ticketPriceDescriptionZh, segmentBufferZh FROM routes")
        routes = c.fetchall()
        
        print(f"Found {len(routes)} routes.")
        
        for i, r in enumerate(routes):
            rid = str(r['route_unique_id'])
            # if rid != '11152': continue
            # if rid not in ['15373', '10334', '10417']: continue
            
            success = False
            # 1. Try Segment Buffer Text
            if r['segmentBufferZh'] and r['segmentBufferZh'].strip():
                success = process_text_buffer_route(c, rid, r['segmentBufferZh'], r['nameZh'])
            
            # 2. Fallback to Standard (Ticket Price Description)
            if not success:
                success = process_standard_route(c, rid, r['ticketPriceDescriptionZh'], r['nameZh'])
                
            if i % 100 == 0:
                print(f"[{i+1}/{len(routes)}] Route {rid} processed. Success: {success}")

            
            # Incremental commit every 50 routes to let user see progress
            if i % 50 == 0:
                conn.commit()
            
        print("Committing final changes...")
        conn.commit()
        print("Done.")
        conn.close()
        
    except Exception as e:
        sys.stderr.write(f"Global Error: {repr(e)}\n")


def parse_buffer_text(text):
    if not text: return []
    
    # Pre-process text to handle '->' and '→' as delimiter
    text = text.replace('->', '-').replace('→', '-')

    # 1. Normalize delimiters
    text = re.sub(r'([(（]?)((去|回|往|返)[程]?)[:：]?', r' \1\2', text)
    # Normalize various dash-like characters to hyphen
    # Includes: - (hyphen), — (em dash), ~ (tilde), ～ (fullwidth tilde), － (fullwidth hyphen), ─ (box drawing light horizontal), ― (horizontal bar)
    text = re.sub(r'\s*[-—~～－─―]\s*', '-', text)
    # Remove numbering like "1.", "2."
    text = re.sub(r'\d+\.', ' ', text)
    # Replace (含...) with &... for alternative matches
    text = re.sub(r'[(（]含\s*(.*?)\s*[)）]', r'&\1', text)
    
    normalized = text.replace("分段緩衝區：", "").replace("緩衝區：", "").replace("、", "|").replace("，", "|").replace("；", "|").replace(";", "|")
    
    # 2. Extract Direction Blocks
    tokens = re.split(r'([|\s]*[(（]?(?:去|往)[程]?[:：]?[)）]?[|\s]*|[|\s]*[(（]?(?:回|返)[程]?[:：]?[)）]?[|\s]*)', normalized)
    
    parsed_ranges = []
    current_dir = None # None = Both
    
    for token in tokens:
        if not token.strip(): continue
        
        # Detect Header
        if '去' in token or '往' in token:
            current_dir = 0
            continue
        elif '回' in token or '返' in token:
            current_dir = 1
            continue
            
        # Process Content
        raw_segments = re.split(r'[|\s]+', token.strip())
        for seg in raw_segments:
             if not seg.strip(): continue
             
             parts = seg.split('-')
             
             if len(parts) >= 2:
                start = parts[0].strip()
                end = parts[-1].strip()
                
                # Cleanup residual parens and quotes
                while start.startswith('(') and start.count('(') > start.count(')'): start = start[1:]
                while end.endswith(')') and end.count(')') > end.count('('): end = end[:-1]
                
                start = start.replace('「', '').replace('」', '').replace("'", "").replace('"', '').strip()
                end = end.replace('「', '').replace('」', '').replace("'", "").replace('"', '').strip()
                
                if start and end:
                    parsed_ranges.append((start, end, current_dir))
             elif len(parts) == 1 and parts[0].strip():
                # Single stop buffer support
                name = parts[0].strip()
                # Cleanup
                while name.startswith('(') and name.count('(') > name.count(')'): name = name[1:]
                while name.endswith(')') and name.count(')') > name.count('('): name = name[:-1]
                name = name.replace('「', '').replace('」', '').replace("'", "").replace('"', '').strip()
                
                if name:
                    parsed_ranges.append((name, name, current_dir))
                        
    return parsed_ranges

def process_text_buffer_route(cursor, rid, buffer_text, route_name):
    if '232' in route_name:
         print(f"[DEBUG 232] Raw Buffer: {buffer_text!r}")
         
    ranges = parse_buffer_text(buffer_text)
    
    if '232' in route_name:
         print(f"[DEBUG 232] Parsed Ranges: {ranges}")
    
    if not ranges:
        return False
        
    return apply_buffer_logic(cursor, rid, ranges, route_name)

def process_standard_route(cursor, rid, desc_text, route_name):
    if not desc_text: return False
    # Use same parser for ticket description
    ranges = parse_buffer_text(desc_text)
    if not ranges:
        return False
        
    return apply_buffer_logic(cursor, rid, ranges, route_name)

def clean_name(n):
    n = n.replace('（', '(').replace('）', ')')
    n = n.replace('臺', '台')
    # Strict mode: keep parens content
    return n.strip()

def compute_buffer_events(stops, ranges=None, route_name="", manual_zones=None):
    events = {}
    for s in stops:
        events[s['seqNo']] = []
        
    # =========================================================
    # PASS 1.5: Special Turnaround Rules (Loaded from JSON)
    # =========================================================
    import json
    import os
    
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'static', 'special_turnaround_rules.json')
    special_rules = []
    if os.path.exists(rules_path):
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                special_rules = json.load(f)
        except Exception as e:
            print(f"Error loading special rules: {e}")
    
    # Track which sequences are Official Starts/Ends (for Pass 2 blocking)
    official_starts = set()
    official_ends = set()

    if special_rules:
        # Helper for rules
        def rule_clean(n):
             return clean_name(n)
             
        stop_names_cleaned = [rule_clean(s['nameZh']) for s in stops]
        
        for rule in special_rules:
            seq_target = [rule_clean(n) for n in rule.get('sequence', [])]
            trigger_stop = rule_clean(rule.get('trigger_stop', ''))
            if not seq_target or not trigger_stop: continue
            
            # Sliding window search for sequence
            n = len(seq_target)
            for i in range(len(stops) - n + 1):
                window = stop_names_cleaned[i : i+n]
                if window == seq_target:
                    try:
                        rel_idx = seq_target.index(trigger_stop)
                    except ValueError:
                        continue 
                    
                    abs_idx = i + rel_idx
                    s_trigger = stops[abs_idx]
                    
                    is_turnaround = False
                    if abs_idx > 0:
                        if s_trigger['goBack'] == 1 and stops[abs_idx-1]['goBack'] == 0:
                            is_turnaround = True
                    if abs_idx < len(stops) - 1:
                        if s_trigger['goBack'] == 0 and stops[abs_idx+1]['goBack'] == 1:
                            is_turnaround = True
                    
                    if is_turnaround:
                        # print(f"    [Pass 1.5] Special Rule '{rule.get('rule_name')}' applied at Seq {s_trigger['seqNo']}")
                        for buf_idx in range(i + 1, i + n - 1):
                            seq = stops[buf_idx]['seqNo']
                            if 'start' not in events[seq]: events[seq].append('start')
                            if 'end' not in events[seq]: events[seq].append('end')
                            official_starts.add(seq)
                            official_ends.add(seq)

    # =========================================================
    # PASS 1: Official Buffer Marking (Index Resolution or Manual)
    # =========================================================
    
    # Priority A: Manual Zones (Structured Data)
    if manual_zones:
        for start_seq, end_seq in manual_zones:
            if start_seq <= end_seq:
                if 'start' not in events[start_seq]: 
                    events[start_seq].append('start')
                    official_starts.add(start_seq)
                if 'end' not in events[end_seq]: 
                    events[end_seq].append('end')
                    official_ends.add(end_seq)
    
    # Priority B: Text Parsing (Index Resolution)
    elif ranges:
        def match_name(stop_n, pattern_str):
            # Support A&B syntax
            patterns = pattern_str.split('&')
            s_clean = clean_name(stop_n).replace('站', '')
            # Base name without parens
            s_base = s_clean.split('(')[0] if '(' in s_clean else s_clean
            
            for p in patterns:
                p_clean = clean_name(p).replace('站', '')
                p_base = p_clean.split('(')[0] if '(' in p_clean else p_clean
                
                # Match Full or Base
                if p_clean == s_clean or p_base == s_base:
                    return True
            return False

        unmatched_ranges = []
        
        for start_src, end_src, range_dir in ranges:
            range_matched_any = False # Track if this range matched at least one direction
            
            for direction in [0, 1]:
                if range_dir is not None and range_dir != direction: continue
                
                dir_stops = [s for s in stops if s['goBack'] == direction]
                if not dir_stops: continue
                
                match_starts = []
                match_ends = []
                
                for s in dir_stops:
                    s_name = clean_name(s['nameZh'])
                    if match_name(s_name, start_src):
                        match_starts.append(s['seqNo'])
                    if match_name(s_name, end_src):
                        match_ends.append(s['seqNo'])
                
                if not match_starts or not match_ends:
                    continue
                
                all_idxs = match_starts + match_ends
                min_seq = min(all_idxs)
                max_seq = max(all_idxs)
                
                if min_seq <= max_seq: # Allow single stop buffer
                    range_matched_any = True
                    if 'start' not in events[min_seq]:
                        events[min_seq].append('start')
                        official_starts.add(min_seq)
                        
                    if 'end' not in events[max_seq]:
                        events[max_seq].append('end')
                        official_ends.add(max_seq)
                    # print(f"    [Pass 1] Marked Buffer: {min_seq} (Start) -> {max_seq} (End) [Dir {direction}]")
            
            if not range_matched_any:
                unmatched_ranges.append((start_src, end_src))

        # =========================================================
        # PASS 1.9: Virtual Stop Fallback
        # =========================================================
        # If there are unmatched ranges, try to find "Virtual Stops" (e.g. Highway markers)
        # and assign them as Section Points (Start+End)
        
        if unmatched_ranges:
             # Find all virtual stops (filter by name)
             virtual_keyword = "(虛擬站不停靠)"
             
             for direction in [0, 1]:
                 dir_stops = [s for s in stops if s['goBack'] == direction]
                 if not dir_stops: continue
                 
                 # Find indices of virtual stops in this direction
                 virt_indices = []
                 for i, s in enumerate(dir_stops):
                     if virtual_keyword in s['nameZh']:
                         virt_indices.append(i)
                 
                 if not virt_indices: continue
                 
                 # Group consecutive indices
                 # e.g. [5, 6, 10, 11, 12] -> [[5,6], [10,11,12]]
                 groups = []
                 if virt_indices:
                     current_group = [virt_indices[0]]
                     for x in virt_indices[1:]:
                         if x == current_group[-1] + 1:
                             current_group.append(x)
                         else:
                             groups.append(current_group)
                             current_group = [x]
                     groups.append(current_group)
                 
                 # Apply Unmatched Ranges to Groups
                 # Strategy: Distribute ranges to groups sequentially. 
                 # If ranges > groups, stack the remaining on the last group (or distribute via modulo/saturation).
                 # User Request (965): "Accumulate 5 sets" on the available virtual stops.
                 # We will use saturation: min(i, len(groups)-1)
                 
                 for i in range(len(unmatched_ranges)):
                     # Pick group (saturate at last group)
                     grp_idx = min(i, len(groups) - 1)
                     grp = groups[grp_idx]
                     
                     target_idx = grp[0] # Pick first stop of the group
                     s_target = dir_stops[target_idx]
                     seq = s_target['seqNo']
                     
                     # Force add event (ignoring duplicates - we want stacking)
                     # But Wait! events[seq] is a list. If we add 'start' twice, does update_stops_segments count it twice?
                     # Let's check update_stops_segments Logic:
                     # "for e in evs: if e in [...]: get_on += 1"
                     # YES! It iterates the list literal, so duplicates correspond to multiple increments.
                     
                     events[seq].append('start')
                     official_starts.add(seq)
                     
                     events[seq].append('end')
                     official_ends.add(seq)
                     
                     # print(f"    [Pass 1.9] Virtual Stack: {s_target['nameZh']} (Seq {seq}) - Range {i+1}")

    # =========================================================
    # PASS 2: Turnaround Buffer Marking (Updated Algorithm)
    # =========================================================
    
    # Load Dual Terminal List
    dual_terminal_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'static', 'dual_terminal_routes.json')
    dual_terminal_config = {"exact_match": [], "fuzzy_match": []}
    
    if os.path.exists(dual_terminal_path):
        try:
             with open(dual_terminal_path, 'r', encoding='utf-8') as f:
                 loaded_data = json.load(f)
                 if isinstance(loaded_data, list):
                     dual_terminal_config["exact_match"] = loaded_data
                 elif isinstance(loaded_data, dict):
                     dual_terminal_config = loaded_data
        except: pass
    
    # Load Official Data Corrections (routes with incorrectly duplicated terminal stops)
    corrections_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'static', 'official_data_corrections.json')
    ignore_same_terminal_list = []
    
    if os.path.exists(corrections_path):
        try:
            with open(corrections_path, 'r', encoding='utf-8') as f:
                corrections_data = json.load(f)
                ignore_same_terminal_list = corrections_data.get("ignore_same_terminal", [])
        except: pass
        
    go_stops = [s for s in stops if s['goBack'] == 0]
    back_stops = [s for s in stops if s['goBack'] == 1]
    
    # helper maps
    go_map = { clean_name(s['nameZh']): s['seqNo'] for s in go_stops }
    back_map = { clean_name(s['nameZh']): s['seqNo'] for s in back_stops }
    stops_map = { s['seqNo']: s for s in stops }
    
    if go_stops and back_stops:
        last_go = go_stops[-1]
        first_back = back_stops[0]
        c_last_go = clean_name(last_go['nameZh'])
        c_first_back = clean_name(first_back['nameZh'])
        
        # Check if this route should ignore same-terminal detection (official data error)
        should_ignore_same_terminal = (route_name in ignore_same_terminal_list)
        
        # Check Exact Match (Support both string and object format)
        exact_list = dual_terminal_config.get("exact_match", [])
        dual_terminal_entry = None
        for entry in exact_list:
            if isinstance(entry, str):
                # Legacy string format
                if entry == route_name:
                    dual_terminal_entry = {"route": entry, "loop_range": None}
                    break
            elif isinstance(entry, dict):
                # New object format with loop_range
                if entry.get("route") == route_name:
                    dual_terminal_entry = entry
                    break
        
        is_dual_terminal = (dual_terminal_entry is not None)
        loop_range = dual_terminal_entry.get("loop_range") if dual_terminal_entry else None
        
        # Check Fuzzy Match
        if not is_dual_terminal:
            fuzzy_list = dual_terminal_config.get("fuzzy_match", [])
            for pattern in fuzzy_list:
                if pattern in route_name:
                    is_dual_terminal = True
                    loop_range = None  # Fuzzy match always uses default method
                    break
        
        # Determine if we should treat as disconnected turnaround
        # If route is in ignore_same_terminal list and last_go == first_back, use special loop detection
        treat_as_dual_terminal = False
        use_special_loop_detection = False
        
        if is_dual_terminal:
            treat_as_dual_terminal = True
        elif c_last_go == c_first_back:
            if should_ignore_same_terminal:
                # Official data error - use special loop detection to find correct boundaries
                use_special_loop_detection = True
            else:
                treat_as_dual_terminal = True
        
        # Special case: Official data has duplicate terminal stops (e.g., 232)
        # Find correct loop boundaries by looking for nearest bidirectional stops
        if use_special_loop_detection:
            # Walk backwards from last_go to find last bidirectional stop in go direction
            last_bidi_go_idx = None
            for i in range(len(go_stops) - 2, -1, -1):  # Start from second-to-last
                gs = go_stops[i]
                if clean_name(gs['nameZh']) in back_map:
                    last_bidi_go_idx = i
                    break
            
            # Walk forwards from first_back to find first bidirectional stop in back direction
            first_bidi_back_seq = None
            for i in range(1, len(back_stops)):  # Start from second
                bs = back_stops[i]
                bs_name = clean_name(bs['nameZh'])
                # Skip if this stop has same name as last_go (the duplicate terminal issue)
                if bs_name == c_last_go:
                    continue
                if bs_name in go_map:
                    first_bidi_back_seq = bs['seqNo']
                    break
            
            # Calculate loop boundaries
            # start_loop_seq = first non-bidirectional stop (the stop AFTER last_bidi_go)
            if last_bidi_go_idx is not None and last_bidi_go_idx + 1 < len(go_stops):
                start_loop_seq = go_stops[last_bidi_go_idx + 1]['seqNo']
            else:
                start_loop_seq = last_go['seqNo']  # Fallback to last go stop
            end_loop_seq = first_bidi_back_seq - 1 if first_bidi_back_seq else first_back['seqNo']  # Last non-bidirectional stop
            
            if end_loop_seq in events and start_loop_seq <= end_loop_seq:
                if 'start_of_loop' not in events[start_loop_seq]:
                    events[start_loop_seq].append('start_of_loop')
                    official_starts.add(start_loop_seq)
                if 'end_of_loop' not in events[end_loop_seq]:
                    events[end_loop_seq].append('end_of_loop')
                    official_ends.add(end_loop_seq)
                # print(f"    [Turnaround Pass 2] Special Loop (ignore_same_terminal) at {start_loop_seq} -> {end_loop_seq}")
        
        # Flag to skip normal turnaround detection if already handled
        skip_normal_turnaround = use_special_loop_detection
        
        # Case: Tight U-Turn at same stop (Dual Terminal / Disconnected Turnaround)
        # OR if explicitly listed in dual_terminal_routes
        if treat_as_dual_terminal:
            if loop_range:
                # Use custom loop_range with start_of_loop / end_of_loop
                start_name = loop_range.get("start", "")
                end_name = loop_range.get("end", "")
                
                # Find matching stops by name
                start_seq = None
                end_seq = None
                
                for s in stops:
                    s_clean = clean_name(s['nameZh'])
                    if start_name and clean_name(start_name) in s_clean or s_clean in clean_name(start_name):
                        if start_seq is None:
                            start_seq = s['seqNo']
                    if end_name and clean_name(end_name) in s_clean or s_clean in clean_name(end_name):
                        end_seq = s['seqNo']  # Take the last match
                
                if start_seq is not None and end_seq is not None and start_seq <= end_seq:
                    if 'start_of_loop' not in events[start_seq]:
                        events[start_seq].append('start_of_loop')
                        official_starts.add(start_seq)
                    if 'end_of_loop' not in events[end_seq]:
                        events[end_seq].append('end_of_loop')
                        official_ends.add(end_seq)
                    # print(f"    [Turnaround Pass 2] Custom Loop at {start_seq} -> {end_seq}")
                else:
                    # Fallback to default if name matching fails
                    if 'end_of_go' not in events[last_go['seqNo']]:
                        events[last_go['seqNo']].append('end_of_go')
                        official_ends.add(last_go['seqNo'])
                    if 'start_of_back' not in events[first_back['seqNo']]:
                        events[first_back['seqNo']].append('start_of_back')
                        official_starts.add(first_back['seqNo'])
            else:
                # Use default method (end_of_go / start_of_back)
                if 'end_of_go' not in events[last_go['seqNo']]:
                    events[last_go['seqNo']].append('end_of_go')
                    official_ends.add(last_go['seqNo'])
                    
                if 'start_of_back' not in events[first_back['seqNo']]:
                    events[first_back['seqNo']].append('start_of_back')
                    official_starts.add(first_back['seqNo'])
                # print(f"    [Turnaround Pass 2] Disconnected Turnaround at {last_go['seqNo']} -> {first_back['seqNo']}")
        
        elif not skip_normal_turnaround:
            prev_back_seq = None
            for s in back_stops:
                s_name = clean_name(s['nameZh'])
                curr_back_seq = s['seqNo']
                
                if s_name in go_map:
                    match_go_seq = go_map[s_name]
                    
                    start_cand_seq = 99999
                    for gs in go_stops:
                         if gs['seqNo'] > match_go_seq:
                             if clean_name(gs['nameZh']) in back_map:
                                 continue 
                             
                             start_cand_seq = gs['seqNo']
                             break
                    
                    if start_cand_seq == 99999:
                         if go_stops and match_go_seq == go_stops[-1]['seqNo']:
                             if back_stops:
                                  start_cand_seq = back_stops[0]['seqNo']
                    
                    target_prev = curr_back_seq - 1
                    if target_prev in events:
                         end_cand_seq = target_prev
                    else:
                        if prev_back_seq is None:
                            prev_back_seq = curr_back_seq
                            continue
                        end_cand_seq = prev_back_seq
                        
                    while end_cand_seq >= start_cand_seq:
                         s_end = stops_map.get(end_cand_seq)
                         name_end = clean_name(s_end['nameZh'])
                         if s_end and name_end in go_map and name_end in back_map:
                             end_cand_seq -= 1
                             while end_cand_seq not in events and end_cand_seq >= start_cand_seq:
                                 end_cand_seq -= 1
                         else:
                             break
                    
                    if start_cand_seq <= end_cand_seq: 
                        has_interference = False
                        internal_events = []
                        for seq in range(start_cand_seq + 1, end_cand_seq):
                            if seq in events:
                                ev_list = events[seq]
                                if 'end' in ev_list:
                                    internal_events.append((seq, 'end'))
                                if 'start' in ev_list:
                                    internal_events.append((seq, 'start'))
                                if 'end_of_go' in ev_list or 'start_of_back' in ev_list:
                                    internal_events.append((seq, 'BLOCKER'))

                        if not internal_events:
                            has_interference = False
                        else:
                            blockers = [x for x in internal_events if x[1] == 'BLOCKER']
                            if blockers:
                                has_interference = True
                            else:
                                ends = [x for x in internal_events if x[1] == 'end']
                                starts = [x for x in internal_events if x[1] == 'start']
                                
                                if len(ends) == 1 and len(starts) == 1:
                                    if ends[0][0] < starts[0][0]:
                                         has_interference = False
                                    else:
                                         has_interference = True
                                else:
                                    has_interference = True
                        
                        if not has_interference:
                            if 'start_of_loop' not in events[start_cand_seq]:
                                events[start_cand_seq].append('start_of_loop')
                            
                            if 'end_of_loop' not in events[end_cand_seq]:
                                events[end_cand_seq].append('end_of_loop')
                                
                            break 
                    
                prev_back_seq = curr_back_seq
    
    return events



def update_stops_segments(cursor, rid, stops, events):
    get_on = 1
    get_off = 1
    
    # RID_DEBUG = (rid in ['11245', '16591']) 
    
    for s in stops:
        seq = s['seqNo']
        evs = events.get(seq, [])
        
        # Apply Start (Boarding Inc)
        for e in evs:
            if e in ['start', 'start_of_back', 'start_of_loop']: 
                get_on += 1
            
        # Update Stop
        cursor.execute("UPDATE stops SET segment_boarding = ?, segment_alighting = ? WHERE route_unique_id = ? AND seqNo = ?", (get_on, get_off, rid, seq))

        # Apply End (Alighting Inc - Exclusive)
        for e in evs:
            if e in ['end', 'end_of_go', 'end_of_loop']: 
                get_off += 1
    return True

def apply_buffer_logic(cursor, rid, ranges, route_name):
    cursor.execute("SELECT * FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (rid,))
    stops = cursor.fetchall()

    events = compute_buffer_events(stops, ranges=ranges, route_name=route_name)
    return update_stops_segments(cursor, rid, stops, events)

def fetch_structured_zones(cursor, rid, stops):
    """
    Fetch raw structured fare zones from DB and map to sequences.
    Returns: list of (start_seq, end_seq)
    """
    cursor.execute("SELECT direction, origin_stop_id, destination_stop_id FROM route_fares WHERE route_unique_id = ?", (rid,))
    fares = cursor.fetchall()
    
    if not fares:
        return []
        
    stop_map = {}
    for s in stops:
        k = (int(s['stop_unique_id']), int(s['goBack']))
        stop_map[k] = s['seqNo']
        
    zones = []
    for f in fares:
        direction = int(f['direction'])
        orig_id = int(f['origin_stop_id'])
        dest_id = int(f['destination_stop_id'])
        
        start_seq = stop_map.get((orig_id, direction))
        end_seq = stop_map.get((dest_id, direction))
        
        if start_seq is not None and end_seq is not None:
             zones.append((start_seq, end_seq))
             
    return zones

def process_hybrid_route(cursor, rid, buff_text, route_name, ticket_desc=""):
    cursor.execute("SELECT * FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (rid,))
    stops = cursor.fetchall()
    
    manual_zones = []
    
    # 1. Try Text Parsing First? 
    # User Request: "When text parsing fails, use default (structured) tags"
    # User Request: "Default db marking -> if text fails -> use default"
    # Implies: Try Text. If valid, use Text. If invalid, use Structured.
    
    ranges = None
    if buff_text and buff_text.strip():
        ranges = parse_buffer_text(buff_text)
        
    # 2. If Text Parsing Succeeded (ranges is not empty), use it
    if ranges:
        # print(f"Route {route_name}: Using Text Buffer ({len(ranges)} ranges)")
        events = compute_buffer_events(stops, ranges=ranges, route_name=route_name)
    else:
        # 3. If Text Parsing Failed (or empty), Fallback to Structured
        # print(f"Route {route_name}: Fallback to Structured Data")
        
        # 3.1 Try Structured
        manual_zones = fetch_structured_zones(cursor, rid, stops)
        if manual_zones:
            events = compute_buffer_events(stops, manual_zones=manual_zones, route_name=route_name)
        else:
            # 3.2 Try Ticket Description (Last Resort)
            desc_ranges = parse_buffer_text(ticket_desc)
            if desc_ranges:
                events = compute_buffer_events(stops, ranges=desc_ranges, route_name=route_name)
            else:
                # No buffer info at all, run Turnaround Only (Pass 2)
                events = compute_buffer_events(stops, ranges=[], route_name=route_name)
    
    return update_stops_segments(cursor, rid, stops, events)

def process_structured_fares(cursor, rid, route_name):
    # DEPRECATED / Legacy Wrapper
    cursor.execute("SELECT * FROM stops WHERE route_unique_id = ? ORDER BY seqNo", (rid,))
    stops = cursor.fetchall()
    manual_zones = fetch_structured_zones(cursor, rid, stops)
    if not manual_zones: return False
    
    events = compute_buffer_events(stops, manual_zones=manual_zones, route_name=route_name)
    return update_stops_segments(cursor, rid, stops, events)


            
    return True

if __name__ == "__main__":
    parse_buffer_zones_from_db()
