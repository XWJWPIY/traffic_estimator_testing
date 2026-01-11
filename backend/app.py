from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

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
