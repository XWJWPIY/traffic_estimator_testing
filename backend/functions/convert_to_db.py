import sqlite3
import json
import os
import argparse
import sys

# Ensure we can import from the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import parse_buffer_zones

def create_tables(conn):
    cursor = conn.cursor()
    
    # 建立 routes 資料表
    cursor.execute('DROP TABLE IF EXISTS routes')
    cursor.execute('''
    CREATE TABLE routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_unique_id INTEGER, -- 對應 JSON 中的 Id
        nameZh TEXT,
        departureZh TEXT,
        destinationZh TEXT,
        city TEXT,
        bus_type TEXT, -- 新增車種
        ticketPriceDescriptionZh TEXT, -- 新增票價描述 (for fallback parsing)
        segmentBufferZh TEXT -- 新增分段緩衝文字 (for parsing)
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_routes_name ON routes (nameZh)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_routes_uid ON routes (route_unique_id)')

    # 建立 stops 資料表
    cursor.execute('DROP TABLE IF EXISTS stops')
    cursor.execute('''
    CREATE TABLE stops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stop_unique_id INTEGER,
        route_unique_id INTEGER,
        nameZh TEXT,
        seqNo INTEGER,
        goBack INTEGER,
        longitude REAL,
        latitude REAL,
        address TEXT,
        city TEXT,
        segment_boarding INTEGER, -- 上車所屬段次
        segment_alighting INTEGER -- 下車所屬段次
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stops_route_id ON stops (route_unique_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stops_lookup ON stops (route_unique_id, goBack, seqNo)')
    
    # 建立 route_fares 資料表 (Optional, keeping for reference)
    cursor.execute('DROP TABLE IF EXISTS route_fares')
    cursor.execute('''
    CREATE TABLE route_fares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_unique_id INTEGER,
        direction INTEGER,
        section_sequence INTEGER,
        origin_stop_id INTEGER,
        destination_stop_id INTEGER,
        description TEXT,
        city TEXT
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fares_route ON route_fares (route_unique_id, direction)')
    
    conn.commit()

def import_routes(conn, base_dir):
    json_path = os.path.join(base_dir, 'data', 'merged', 'merged_bus_routes.json')
    if not os.path.exists(json_path):
        print(f"檔案不存在: {json_path}")
        return

    print("正在匯入路線資料...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()
    count = 0

    # Load bus type maps
    bus_type_map_path = os.path.join(base_dir, 'data', 'static', 'bus_type_map.json')
    bus_type_map = {}
    if os.path.exists(bus_type_map_path):
        with open(bus_type_map_path, 'r', encoding='utf-8') as f:
            bus_type_map = json.load(f)
            
    # Logic from process_routes.py
    def determine_bus_type(route_name):
        bus_type = "一般公車"
        
        for type_key, route_list in bus_type_map.items():
            if route_name in route_list:
                return type_key
                
            if "F" in route_name:
                return "新北市新巴士"
                
            if "-" in route_name:
                if "台灣好行-" in route_name:
                    continue
                # If there's a digit before '-', it's New Taipei New Bus (e.g. Fxxx-xxx logic covered or similar?)
                # process_routes.py logic: if ("0" <= route_name[route_name.index("-") - 1] <= "9"): continue
                try:
                    idx = route_name.index("-")
                    if idx > 0 and '0' <= route_name[idx - 1] <= '9':
                        continue # Skip to default or other logic? In original code: continue loop, meaning don't set to "跳蛙" yet
                except ValueError:
                    pass
                    
                bus_type = "跳蛙公車"
                break
        return bus_type

    for city, routes in data.items():
        # routes 結構: { "EssentialInfo": ..., "BusInfo": [...] }
        if not routes or "BusInfo" not in routes:
            continue
            
        for route in routes["BusInfo"]:
            r_name = route.get("nameZh")
            b_type = determine_bus_type(r_name)
            
            # Extract ticketPriceDescriptionZh and segmentBufferZh
            ticket_price_desc = route.get("ticketPriceDescriptionZh")
            segment_buffer_desc = route.get("segmentBufferZh")

            cursor.execute('''
            INSERT INTO routes (route_unique_id, nameZh, departureZh, destinationZh, city, bus_type, ticketPriceDescriptionZh, segmentBufferZh)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                route.get("Id"),
                r_name,
                route.get("departureZh"),
                route.get("destinationZh"),
                city,
                b_type,
                ticket_price_desc,
                segment_buffer_desc
            ))
            count += 1
    
    conn.commit()
    print(f"已匯入 {count} 筆路線資料。")

def import_stops(conn, base_dir):
    json_path = os.path.join(base_dir, 'data', 'merged', 'merged_stops.json')
    if not os.path.exists(json_path):
        print(f"檔案不存在: {json_path}")
        return

    print("正在匯入站牌資料 (這可能需要一點時間)...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()
    count = 0
    
    for city, stops in data.items():
        if not stops or "BusInfo" not in stops:
            continue
            
        batch_data = []
        for stop in stops["BusInfo"]:
            # 轉換 goBack 為整數
            go_back = stop.get("goBack")
            try:
                go_back = int(go_back) if go_back is not None else 0
            except ValueError:
                go_back = 0
                
            batch_data.append((
                stop.get("Id"),
                stop.get("routeId"),
                stop.get("nameZh"),
                stop.get("seqNo"),
                go_back,
                stop.get("longitude"),
                stop.get("latitude"),
                stop.get("address"),
                city,
                None, # segment_boarding, will be updated later
                None  # segment_alighting, will be updated later
            ))
            
            if len(batch_data) >= 10000:
                cursor.executemany('''
                INSERT INTO stops (stop_unique_id, route_unique_id, nameZh, seqNo, goBack, longitude, latitude, address, city, segment_boarding, segment_alighting)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch_data)
                conn.commit()
                count += len(batch_data)
                batch_data = []
                print(f"已處理 {count} 筆站牌資料...")
        
        if batch_data:
            cursor.executemany('''
            INSERT INTO stops (stop_unique_id, route_unique_id, nameZh, seqNo, goBack, longitude, latitude, address, city, segment_boarding, segment_alighting)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            conn.commit()
            count += len(batch_data)

    print(f"已匯入 {count} 筆站牌資料。")

def import_route_fares(conn, base_dir):
    json_path = os.path.join(base_dir, 'data', 'merged', 'merged_bus_route_fare_list.json')
    if not os.path.exists(json_path):
        print(f"檔案不存在: {json_path}")
        return

    print("正在匯入票價結構資料...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()
    
    count = 0
    for city, fares in data.items():
        if not fares:
            continue
        
        actual_fares_list = []
        if isinstance(fares, list):
            for item in fares:
                if isinstance(item, dict) and "RouteFare" in item:
                    actual_fares_list = item["RouteFare"]
                    break
        
        if not actual_fares_list:
            print(f"[{city}] Warning: No RouteFare list found in data.")
            continue
            
        print(f"[{city}] Found {len(actual_fares_list)} routes in RouteFare list.")
            
        batch_data = []
        skip_counts = {"no_section": 0, "no_buffer_container": 0, "empty_buffer": 0, "success": 0, "error": 0}
        
        for fare in actual_fares_list:
            try:
                r_id = fare.get("RouteID")
                pricing_type = fare.get("FarePricingType")
                
                if pricing_type != "SectionFare":
                    skip_counts["no_section"] += 1
                    continue
                    
                section_fare = fare.get("SectionFare", {})
                if not section_fare: 
                    skip_counts["no_section"] += 1
                    continue
                    
                buffer_zones_container = section_fare.get("BufferZones", {})
                if isinstance(buffer_zones_container, str) or not buffer_zones_container:
                    skip_counts["no_buffer_container"] += 1
                    continue
                    
                buffer_zones = buffer_zones_container.get("BufferZone")
                if not buffer_zones:
                    skip_counts["empty_buffer"] += 1
                    continue
                    
                if not isinstance(buffer_zones, list):
                    buffer_zones = [buffer_zones]
                    
                for zone in buffer_zones:
                    try:
                        if not isinstance(zone, dict):
                            continue
                            
                        direction = zone.get("Direction")
                        seq = zone.get("SectionSequence")
                        origin_block = zone.get("FareBufferZoneOrigin", {})
                        origin_id = origin_block.get("OriginStopID")
                        dest_block = zone.get("FareBufferZoneDestination", {})
                        dest_id = dest_block.get("DestinationStopID")
                        desc = "Buffer Zone" # Simplified
                        
                        batch_data.append((r_id, direction, seq, origin_id, dest_id, desc, city))
                        skip_counts["success"] += 1
                        
                    except Exception as e_zone:
                        print(f"Error parsing zone for Route {r_id}: {e_zone}")
                        continue
                        
            except Exception as e:
                skip_counts["error"] += 1
                print(f"Error parsing fare: {e}")
                continue

            if len(batch_data) >= 5000:
                cursor.executemany('''
                INSERT INTO route_fares (route_unique_id, direction, section_sequence, origin_stop_id, destination_stop_id, description, city)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', batch_data)
                conn.commit()
                count += len(batch_data)
                batch_data = []

        if batch_data:
            cursor.executemany('''
            INSERT INTO route_fares (route_unique_id, direction, section_sequence, origin_stop_id, destination_stop_id, description, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            conn.commit()
            count += len(batch_data)
        
        print(f"[{city}] Status: {skip_counts}")

    print(f"已匯入 {count} 筆票價結構資料。")

    print(f"已匯入 {count} 筆票價結構資料。")


def process_segments(conn):
    print("正在計算上下車段次 (使用 parse_buffer_zones 邏輯)...")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT route_unique_id, nameZh, ticketPriceDescriptionZh, segmentBufferZh FROM routes")
        routes = cursor.fetchall()
        
        count = 0
        total = len(routes)
        print(f"總共有 {total} 條路線待處理...")
        
        for r in routes:
            rid = str(r[0]) # route_unique_id
            name = r[1]
            desc = r[2]
            buff = r[3]
            
            success = False
            
            # 0. If "One Segment" (一段票), skip Buffer Parsing (PASS 1) but run PASS 2/3
            # We pass empty ranges [] so no official buffer is marked, but turnaround logic runs.
            if '一段票' in desc:
                parse_buffer_zones.apply_buffer_logic(cursor, rid, [], name)
                count += 1
                if count % 100 == 0:
                     print(f"已處理 {count}/{total} 條路線段次...")
                     conn.commit()
                continue
            
            # 1. Hybrid Process (Text -> Structured -> Turnaround)
            success = parse_buffer_zones.process_hybrid_route(cursor, rid, buff, name, desc)
                
            count += 1
            if count % 100 == 0:
                print(f"已處理 {count}/{total} 條路線段次...")
                conn.commit()
                
        conn.commit()
        print("段次計算完成。")
    except Exception as e:
        print(f"段次計算發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'bus_data.db')
    
    print(f"建立資料庫: {db_path}")
    
    # 若存在則先刪除，確保資料乾淨
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("已刪除舊資料庫")
        except PermissionError:
            print("無法刪除舊資料庫，可能正被使用中。")
            return

    conn = sqlite3.connect(db_path)
    
    try:
        create_tables(conn)
        import_routes(conn, base_dir)
        import_stops(conn, base_dir)
        import_route_fares(conn, base_dir)
        
        # 設定 row_factory 以便讓 parse_buffer_zones 可以用欄位名稱存取 (s['seqNo'])
        conn.row_factory = sqlite3.Row
        
        # 呼叫段次處理邏輯
        process_segments(conn)
        
        print("轉檔完成！")
    except Exception as e:
        print(f"轉檔失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
