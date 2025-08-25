from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
    "市民小巴", "內科專車", "跳蛙公車"
]

# 新增的健康檢查 API 端點
@app.route('/health', methods=['GET'])
def health_check():
    """
    健康檢查 API，檢查伺服器是否在線。
    """
    return jsonify({"status": "ok"}), 200

# 車種輸入版票價計算 API
@app.route('/calculate_fare', methods=['POST'])
def calculate_fare():
    try:
        # 從前端接收 JSON 格式的數據
        data = request.get_json()

        # print(data)

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