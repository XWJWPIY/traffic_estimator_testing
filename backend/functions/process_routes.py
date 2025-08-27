import json
import os


def get_type(merged_data:str, bus_type_map:dict, bus_other_name_map:dict,return_routes:dict, city:str):
    for route in merged_data.get(city).get("BusInfo"):
        route_name = route.get("nameZh")

        # print(route_name, end= "  ")
        
        bus_type = "一般公車"
        other_route_name = None

        if (route_name in bus_other_name_map[city]):
            other_route_name = bus_other_name_map[city][route_name]

        for bus_type_key, bus_type_value in bus_type_map.items():
            if route_name in bus_type_value:
                bus_type = bus_type_key
                break

            if "F" in route_name:
                bus_type = "新北市新巴士"
                break
            if "-" in route_name:
                if ("台灣好行-" in route_name):
                    continue
                if ("0" <= route_name[route_name.index("-") - 1] <= "9"): # 如果路線名稱 - 前方有數字，是新北市新巴士
                    continue
                bus_type = "跳蛙公車"
                break

        # print(bus_type)

        if route_name and bus_type:
            return_routes[route_name] = {
                "RouteName": route_name,
                "BusType": bus_type,
                "City": city,
                "OtherRouteName": other_route_name
            }
    

def process_and_save_routes():
    """
    從合併資料中提取路線名稱、車種、所屬地，並儲存為單獨的 JSON 檔案。
    """
    # 根據腳本位置設定資料目錄
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    merged_file = os.path.join(base_dir, 'data', 'merged', 'merged_bus_routes.json')
    bus_type_file = os.path.join(base_dir, 'data', 'static', 'bus_type_map.json')
    bus_other_name_file = os.path.join(base_dir, 'data', 'static', 'bus_other_name.json')
    output_dir = os.path.join(base_dir, 'data', 'processed')
    output_file = os.path.join(output_dir, 'all_routes.json')

    all_routes = {}

    try:
        # 讀取合併後的資料
        if not os.path.exists(merged_file):
            print(f"錯誤：找不到合併資料檔案 {merged_file}")
            return

        with open(merged_file, 'r', encoding='utf-8') as f:
            merged_data = json.load(f)

        # 讀取車種對照表
        if not os.path.exists(bus_type_file):
            print(f"錯誤：找不到車種對照表檔案 {bus_type_file}")
            return

        with open(bus_type_file, 'r', encoding='utf-8') as f:
            bus_type_map = json.load(f)

        if not os.path.exists(bus_other_name_file):
            print(f"錯誤：找不到車種其他名稱檔案 {bus_other_name_file}")
            return

        with open(bus_other_name_file, 'r', encoding='utf-8') as f:
            bus_other_name_map = json.load(f)

        # 處理台北市公車資料
        get_type(merged_data, bus_type_map, bus_other_name_map, all_routes, "taipei")

        # 處理新北市公車資料
        get_type(merged_data, bus_type_map, bus_other_name_map, all_routes, "newtaipei")

        # 字元排序
        all_routes = dict(sorted(list(all_routes.items())))

        # print(all_routes)

        # 確保輸出目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 儲存處理後的資料
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_routes, f, ensure_ascii=False, indent=4)
        
        print(f"路線資料已成功處理並儲存至 {output_file}")
        
    except Exception as e:
        print(f"處理路線資料時發生錯誤: {e}")

if __name__ == "__main__":
    process_and_save_routes()