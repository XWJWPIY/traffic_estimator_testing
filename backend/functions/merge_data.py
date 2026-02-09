import json
import os

def merge_specific_file(base_dir, file_name, output_name):
    """
    通用合併函式：
    讀取台北和新北的指定檔案，並合併成一個檔案。
    結構為: { "taipei": ..., "newtaipei": ... }
    """
    taipei_file = os.path.join(base_dir, 'data', 'taipei', file_name)
    new_taipei_file = os.path.join(base_dir, 'data', 'newtaipei', file_name)
    output_dir = os.path.join(base_dir, 'data', 'merged')
    output_file = os.path.join(output_dir, output_name)

    merged_data = {
        "taipei": None,
        "newtaipei": None
    }

    try:
        # 讀取台北資料
        if os.path.exists(taipei_file):
            print(f"讀取台北資料: {file_name}")
            with open(taipei_file, 'r', encoding='utf-8') as f:
                merged_data["taipei"] = json.load(f)

        # 讀取新北資料
        if os.path.exists(new_taipei_file):
            print(f"讀取新北資料: {file_name}")
            with open(new_taipei_file, 'r', encoding='utf-8') as f:
                merged_data["newtaipei"] = json.load(f)

        # 這裡檢查一下是否至少有一邊有讀到，避免產生全空的廢檔 (看需求)
        # 但為了保持格式一致，即使是 None 也寫入可能是預期行為

        # 確保輸出目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 儲存合併後的資料
        print(f"正在儲存合併檔案: {output_name}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        print(f"資料已成功合併並儲存至 {output_file}")
        
    except FileNotFoundError as e:
        print(f"找不到檔案: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析失敗 ({file_name}): {e}")
    except Exception as e:
        print(f"合併資料時發生錯誤 ({file_name}): {e}")

def merge_all_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. 路線資料
    merge_specific_file(base_dir, 'bus_routes.json', 'merged_bus_routes.json')
    
    # 2. 站牌資料 (新增)
    merge_specific_file(base_dir, 'stops.json', 'merged_stops.json')
    
    # 3. 站牌位置資料 (新增)
    merge_specific_file(base_dir, 'stop_locations.json', 'merged_stop_locations.json')

    # 4. 票價資料 (新增)
    merge_specific_file(base_dir, 'bus_route_fare_list.json', 'merged_bus_route_fare_list.json')

if __name__ == "__main__":
    merge_all_data()