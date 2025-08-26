import json
import os

def merge_bus_data():
    """
    讀取台北和新北的公車資料，並合併成一個檔案。
    """
    # 根據腳本位置設定資料目錄
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    taipei_file = os.path.join(base_dir, 'data', 'taipei', 'bus_routes.json')
    new_taipei_file = os.path.join(base_dir, 'data', 'newtaipei', 'bus_routes.json')
    output_dir = os.path.join(base_dir, 'data', 'merged')
    output_file = os.path.join(output_dir, 'merged_bus_routes.json')

    merged_data = {
        "taipei": [],
        "newtaipei": []
    }

    try:
        # 讀取台北資料
        if os.path.exists(taipei_file):
            with open(taipei_file, 'r', encoding='utf-8') as f:
                merged_data["taipei"] = json.load(f)

        # 讀取新北資料
        if os.path.exists(new_taipei_file):
            with open(new_taipei_file, 'r', encoding='utf-8') as f:
                merged_data["newtaipei"] = json.load(f)

        # 確保輸出目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 儲存合併後的資料
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        print(f"資料已成功合併並儲存至 {output_file}")
        
    except FileNotFoundError as e:
        print(f"找不到檔案: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON 解析失敗: {e}")
    except Exception as e:
        print(f"合併資料時發生錯誤: {e}")

if __name__ == "__main__":
    merge_bus_data()