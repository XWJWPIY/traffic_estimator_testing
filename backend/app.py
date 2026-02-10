from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import sqlite3

# 設定前端資料夾路徑
FRONTEND_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_FOLDER)
CORS(app)  # 允許跨域請求（GitHub Pages 需要）


# ============================================
# 靜態檔案服務（模擬 GitHub Pages）
# ============================================
@app.route('/')
def serve_index():
    """提供首頁"""
    return send_from_directory(FRONTEND_FOLDER, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """提供其他靜態檔案（HTML, CSS, JS）"""
    return send_from_directory(FRONTEND_FOLDER, filename)



# 定義票價與公車段數
FARE_RATES = {
    "full_fare": 15,
    "student_fare": 12,
    "half_fare": 8
}

# 打折扣款費用
DISCOUNT_RATES = {
    "full_fare": -8,
    "student_fare": -6,
    "half_fare": -4
}

BUS_OPTIONS = [
    "台北市一般公車", "新北市一般公車", "幹線公車", "快速公車",
    "市民小巴", "內科專車", "跳蛙公車", "新北市新巴士"
]

CITIES = {"taipei": "台北市", "newtaipei": "新北市"}

# 新增的健康檢查 API 端點
@app.route('/health', methods=['GET'])
def health_check():
    """
    健康檢查 API，檢查伺服器是否在線。
    """
    return jsonify({"status": "ok"}), 200

# 新增的 API 端點，用來載入所有公車路線資料
@app.route('/api/routes', methods=['GET'])
def get_routes():
    """
    載入所有公車路線資料。
    """
    try:
        file_path = os.path.join(app.root_path, 'data', 'processed', 'all_routes.json')
        
        # 檢查檔案是否存在，以避免 FileNotFoundError
        if not os.path.exists(file_path):
            return jsonify({"error": "all_routes.json file not found at the specified path"}), 500

        with open(file_path, 'r', encoding='utf-8') as f:
            all_routes = json.load(f)
            # print(routes)

        routes = []

        for route in all_routes.keys():
            temp_line_dict = {"RouteName" : route}
            temp_line_dict["OutputName"] = route
            if (all_routes[route]["OtherRouteName"] != None):
                temp_line_dict["OutputName"] = all_routes[route]["OtherRouteName"] + " " + route
            routes.append(temp_line_dict)

        # 將所有路線分為「幹線」路線和其他路線
        trunk_routes = [route for route in routes if "幹線" in route["OutputName"]]
        trunk_routes.sort(key=lambda x: x["OutputName"])
        other_routes = [route for route in routes if "幹線" not in route["OutputName"]]
        
        # 將「幹線」路線列表放在其他路線列表前面，然後返回合併後的列表
        sorted_routes = trunk_routes + other_routes
        # print(sorted_routes)
        return jsonify(sorted_routes)
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/bus_options', methods=['GET'])
def get_bus_options():
    """
    取得所有不重複的公車種類清單。
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        # 排除 null 或空字串
        cursor.execute("SELECT DISTINCT bus_type FROM routes WHERE bus_type IS NOT NULL AND bus_type != '' ORDER BY bus_type")
        types = [row[0] for row in cursor.fetchall()]

        # 指定排序邏輯 (可選)
        # 例如: 一般公車 > 幹線公車 > ...
        # 目前先依資料庫 DISTINCT 排序 (通常是字元序)
        # 如果需要特定順序，可以在這裡重新排序 list

        # Example custom sort:
        priority = ["台北市一般公車", "新北市一般公車", "幹線公車"]
        
        def sort_key(t):
            if t in priority:
                return priority.index(t)
            return 999 # Others at the end

        types.sort(key=sort_key)
        
        return jsonify(types)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


def get_db_connection():
    db_path = os.path.join(app.root_path, 'data', 'bus_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/route_stops', methods=['GET'])
def get_route_stops():
    """
    根據路線名稱查詢所有站牌 (包含去程與返程)
    Query Params: route_name (e.g. "617")
    """
    route_name = request.args.get('route_name')
    if not route_name:
        return jsonify({"error": "Missing route_name parameter"}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 查詢 Route ID
        # 這裡可能會有多筆 (例如不同城市有相同路線名)，目前先取第一筆，或回傳列表讓前端選
        # 為簡化，假設路線名能唯一識別，或由前端傳入 City 更好。
        # 目前先只用 route_name 查。
        cursor.execute('SELECT route_unique_id, nameZh, city FROM routes WHERE nameZh = ?', (route_name,))
        routes = cursor.fetchall()
        
        if not routes:
            return jsonify({"error": f"Route '{route_name}' not found"}), 404

        # 暫時取第一個匹配的路線 (之後可優化支援多個)
        target_route = routes[0]
        route_id = target_route['route_unique_id']
        
        # 2. 查詢站牌
        cursor.execute('''
            SELECT nameZh, goBack, seqNo, segment_boarding, segment_alighting
            FROM stops 
            WHERE route_unique_id = ? 
            ORDER BY goBack, seqNo
        ''', (route_id,))
        
        stops = cursor.fetchall()
        
        outbound = []
        inbound = []
        
        for stop in stops:
            stop_data = {
                "name": stop['nameZh'], 
                "seq": stop['seqNo'],
                "boarding": stop['segment_boarding'],
                "alighting": stop['segment_alighting']
            }
            if stop['goBack'] == 0:
                outbound.append(stop_data)
            else:
                inbound.append(stop_data)
                
        # 載入雙端發車列表
        dual_terminal_list = []
        static_folder = os.path.join(app.root_path, 'data', 'static')
        dual_list_path = os.path.join(static_folder, 'dual_terminal_routes.json')
        if os.path.exists(dual_list_path):
             with open(dual_list_path, 'r', encoding='utf-8') as f:
                 dual_terminal_list = json.load(f)

        # 載入官方資料誤植清單
        corrections_path = os.path.join(static_folder, 'official_data_corrections.json')
        ignore_same_terminal = []
        if os.path.exists(corrections_path):
             with open(corrections_path, 'r', encoding='utf-8') as f:
                 corrections = json.load(f)
                 ignore_same_terminal = corrections.get('ignore_same_terminal', [])

        warning_msg = ""
        # 1. 檢查是否在手動列表中
        is_manual_dual = False
        for d in dual_terminal_list["exact_match"]:
            if d == target_route['nameZh']: # Exact match
                is_manual_dual = True
                break
            
        for d in dual_terminal_list["fuzzy_match"]:
            if d in target_route['nameZh']: # Fuzzy match
                is_manual_dual = True
                break
        
        if is_manual_dual:
             warning_msg = "⚠️ 注意：此路線去程不接駛返程。"
        
        # 2. 啟發式檢查：去程末站 vs 返程首站 名稱相同（排除已確認的官方誤植路線）
        elif outbound and inbound and target_route['nameZh'] not in ignore_same_terminal:
             last_out = outbound[-1]['name']
             first_in = inbound[0]['name']
             if last_out == first_in:
                  warning_msg = f"⚠️ 提醒：此路線末端為折返站 [{last_out}]，請確認是否需重新購票或下車。"

        # 使用官方表定起訖點 (routes 資料表已存)
        cursor.execute('SELECT departureZh, destinationZh FROM routes WHERE route_unique_id = ?', (route_id,))
        route_info = cursor.fetchone()
        outbound_dest = route_info['destinationZh'] if route_info else ""
        inbound_dest = route_info['departureZh'] if route_info else ""

        return jsonify({
            "route_name": target_route['nameZh'],
            "city": target_route['city'],
            "outbound": outbound,
            "inbound": inbound,
            "outbound_dest": outbound_dest,
            "inbound_dest": inbound_dest,
            "warning": warning_msg
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# 車種輸入版票價計算 API
@app.route('/type_calculate_fare', methods=['POST'])
def type_calculate_fare():
    try:
        # 從前端接收 JSON 格式的數據
        data = request.get_json()

        fare_type = data.get('fare_type')
        bus_trips = data.get('bus_trips')

        # 檢查接收到的數據是否完整
        if not fare_type or not bus_trips:
            return jsonify({"error": "Invalid data format"}), 400

        # 檢查票種是否存在
        if fare_type not in FARE_RATES:
            return jsonify({"error": "Invalid fare type"}), 400

        # 獲取單段票價
        rate_per_trip = FARE_RATES[fare_type]
        discount_per_trip = DISCOUNT_RATES[fare_type]
        total_fare = 0

        # 遍歷每組搭乘數據並計算總價
        # 紀錄前一段車種
        previous_bus_type = None

        for trip in bus_trips:
            trip_count = trip.get('trip_count')
            now_bus_type = trip.get('bus_type')
            if not isinstance(trip_count, int) or trip_count <= 0:
                return jsonify({"error": "Trip count must be a non-negative integer"}), 400

            # 新北市新巴士免費且不須刷卡，不計費也不影響轉乘折扣
            if now_bus_type == "新北市新巴士":
                continue
            
            # 總費用 = 單段票價 * 搭乘段數
            total_fare += (rate_per_trip * trip_count)
            total_fare += (is_get_discount(previous_bus_type, now_bus_type) * discount_per_trip)
            previous_bus_type = now_bus_type

        # 返回 JSON 格式的結果
        return jsonify({"total_fare": total_fare})

    except Exception as e:
        # 處理任何可能發生的錯誤
        return jsonify({"error": str(e)}), 500
    
@app.route('/line_calculate_fare', methods=['POST'])
def line_calculate_fare():
    """
    接收路線號碼和票種，返回總票價。
    """
    try:
        data = request.get_json()
        bus_trips = data.get('bus_trips')  # 從前端接收路線名稱列表
        fare_type = data.get('fare_type', 'full_fare')

        print(data)
        print(bus_trips)
        print(fare_type)


        # 載入所有路線資料以查詢車種
        file_path = os.path.join(app.root_path, 'data', 'processed', 'all_routes.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            all_routes = json.load(f)

        total_fare = 0
        previous_bus_type = None

        # 檢查票種是否存在
        if fare_type not in FARE_RATES:
            return jsonify({"error": "Invalid fare type"}), 400
            
        rate_per_trip = FARE_RATES.get(fare_type)
        discount_per_trip = DISCOUNT_RATES.get(fare_type)


        for trip in bus_trips:
            trip_count = trip.get('trip_count')
            line_name = trip.get('line_name')

            route_info = all_routes.get(line_name)

            if not route_info:
                return jsonify({"error": f"Route '{line_name}' not found"}), 400

            now_bus_type = route_info.get('BusType')
            if (now_bus_type == "一般公車"):
                now_bus_type = CITIES.get(route_info.get('City')) + now_bus_type

            if (now_bus_type == "新北市新巴士"):
                continue

            if not isinstance(trip_count, int) or trip_count <= 0:
                return jsonify({"error": "Trip count must be a non-negative integer"}), 400
            
            # 總費用 = 單段票價 * 搭乘段數
            total_fare += (rate_per_trip * trip_count)
            total_fare += (is_get_discount(previous_bus_type, now_bus_type) * discount_per_trip)
            previous_bus_type = now_bus_type

            
        return jsonify({"total_fare": total_fare})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def is_get_discount(previous_bus_type: str, now_bus_type: str):
    if (previous_bus_type == None):
        return 0
    
    # 無打折轉乘方向 (dict) [key = 前一段車種, value = 後一段車種 list]
    without_discount_dict = {
        "台北市一般公車": ["台北市一般公車","新北市一般公車"],
        "新北市一般公車": ["台北市一般公車","新北市一般公車"],
        "市民小巴": ["新北市一般公車"],
        "內科專車": ["新北市一般公車"]
    }

    if (without_discount_dict.get(previous_bus_type) != None):
        for i in without_discount_dict.get(previous_bus_type):
            if (i == now_bus_type):
                return 0
    return 1

if __name__ == '__main__':
    # 在本地運行，方便測試
    app.run(debug=True)
