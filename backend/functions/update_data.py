import argparse
import requests
import gzip
import json
import os

# 公車路線資料的下載網址
TAIPEI_URL = "https://tcgbusfs.blob.core.windows.net/blobbus/GetRoute.gz"
NEWTAIPEI_URL = "https://tcgbusfs.blob.core.windows.net/ntpcbus/GetRoute.gz"

def fetch_and_decompress(url, output_dir):
    """
    從指定網址下載 .gz 檔案並解壓縮，並儲存為 JSON。
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        decompressed_data = gzip.decompress(response.content)
        decoded_data = decompressed_data.decode('utf-8')
            
        print("資料下載並解壓縮成功。")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, 'bus_routes.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json.loads(decoded_data), f, ensure_ascii=False, indent=4)
            
        print(f"資料已成功儲存至 {output_file}")
        
    except Exception as e:
        print(f"執行時發生錯誤: {e}")

def main():
    # 使用 argparse 函式庫來解析命令列參數
    parser = argparse.ArgumentParser(description="Update bus route data for different cities.")
    parser.add_argument('city', type=str, help="The city to fetch data for.")
    
    args = parser.parse_args()

    # 根據腳本位置設定輸出目錄
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, 'data', args.city)

    print(f"開始更新 {args.city} 的公車資料...")
    
    if args.city == 'taipei':
        fetch_and_decompress(TAIPEI_URL, output_dir)
    elif args.city == 'newtaipei':
        fetch_and_decompress(NEWTAIPEI_URL, output_dir)
    else:
        print(f"找不到 {args.city} 的資料來源。")

if __name__ == "__main__":
    main()