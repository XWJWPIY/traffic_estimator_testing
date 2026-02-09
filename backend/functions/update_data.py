import argparse
import requests
import gzip
import json
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 公車路線資料的下載網址 (從環境變數讀取)
TAIPEI_GETROUTE_URL = os.getenv("TAIPEI_GETROUTE_URL")
NEWTAIPEI_GETROUTE_URL = os.getenv("NEWTAIPEI_GETROUTE_URL")

TAIPEI_GETSTOP_URL = os.getenv("TAIPEI_GETSTOP_URL")
NEWTAIPEI_GETSTOP_URL = os.getenv("NEWTAIPEI_GETSTOP_URL")

TAIPEI_GETSTOPLOCATION_URL = os.getenv("TAIPEI_GETSTOPLOCATION_URL")
NEWTAIPEI_GETSTOPLOCATION_URL = os.getenv("NEWTAIPEI_GETSTOPLOCATION_URL")

import xml.etree.ElementTree as ET

def xml_to_dict(element):
    """
    遞迴將 XML Element 轉換為 Dict。
    處理 Namespace, Attributes, Text content 與 Children。
    """
    # 移除 Namespace URI (例如 {http://...}Tag -> Tag)
    tag = element.tag.split('}')[-1]
    
    data = {}
    
    # 處理屬性 (Attributes)
    if element.attrib:
        data.update(element.attrib)
            
    # 處理子節點 (Children)
    if len(element) > 0:
        for child in element:
            child_data = xml_to_dict(child)
            child_tag = child.tag.split('}')[-1]
            
            # 若已有相同 Tag，轉為 List
            if child_tag in data:
                if not isinstance(data[child_tag], list):
                    data[child_tag] = [data[child_tag]]
                data[child_tag].append(child_data[child_tag]) # 注意這裡取出 child value
            else:
                data[child_tag] = child_data[child_tag] # Unpack child dict
    else:
        # 若無子節點，則取 Text
        text = element.text.strip() if element.text else ""
        return {tag: text} if not data else {tag: text, **data}

    return {tag: data}


def fetch_and_decompress(url, output_dir, output_filename):
    """
    從指定網址下載 .gz 檔案並解壓縮，並儲存為 JSON。
    若內容為 XML (開頭為 <)，則自動轉換為 JSON。
    """
    if not url:
        print(f"警告: 未提供 URL (檔案: {output_filename})，跳過下載。")
        return

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        decompressed_data = gzip.decompress(response.content)
        decoded_data = decompressed_data.decode('utf-8')
        
        # 檢查是否為 XML
        if decoded_data.strip().startswith('<'):
            print(f"偵測到 XML 格式 ({output_filename})，正在轉換為 JSON...")
            try:
                # 預處理: 移除可能的 encoding header 以避免某些 parse error
                # root = ET.fromstring(decoded_data)
                
                # 使用 iterparse 或 fromstring
                root = ET.fromstring(decoded_data)
                
                xml_data = []
                # 假設 Root 下的第一層就是各個資料項目 (例如 <BusRouteFareList> -> <RouteFare>...)
                # 我們把每一項轉成 Dict
                for child in root:
                    child_dict = xml_to_dict(child)
                    # xml_to_dict 回傳的是 {Tag: Content}，我們通常只需要 Content
                    # 但為了保險，我們把 key 也留著，或者 print 出來看看
                    # 通常 List 的 Item 我們只取 value
                    key = list(child_dict.keys())[0]
                    xml_data.append(child_dict[key])
                
                final_data = xml_data
                
            except ET.ParseError as e:
                print(f"XML 解析失敗: {e}")
                # 嘗試印出部分內容除錯
                print(f"前 200 字元: {decoded_data[:200]}")
                return
        else:
            final_data = json.loads(decoded_data)
            
        print(f"資料下載並解壓縮成功: {output_filename}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, output_filename)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
            
        print(f"資料已成功儲存至 {output_file}")
        
    except Exception as e:
        print(f"執行時發生錯誤 ({output_filename}): {e}")

def main():
    # 使用 argparse 函式庫來解析命令列參數
    parser = argparse.ArgumentParser(description="Update bus data (routes, stops, locations) for different cities.")
    parser.add_argument('city', type=str, help="The city to fetch data for (taipei or newtaipei).")
    
    args = parser.parse_args()

    # 根據腳本位置設定輸出目錄
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, 'data', args.city)

    print(f"開始更新 {args.city} 的公車資料...")
    
    if args.city == 'taipei':
        fetch_and_decompress(TAIPEI_GETROUTE_URL, output_dir, 'bus_routes.json')
        fetch_and_decompress(TAIPEI_GETSTOP_URL, output_dir, 'stops.json')
        fetch_and_decompress(TAIPEI_GETSTOPLOCATION_URL, output_dir, 'stop_locations.json')
        fetch_and_decompress(os.getenv("TAIPEI_GETBUSROUTEFARELIST_URL"), output_dir, 'bus_route_fare_list.json')
    elif args.city == 'newtaipei':
        fetch_and_decompress(NEWTAIPEI_GETROUTE_URL, output_dir, 'bus_routes.json')
        fetch_and_decompress(NEWTAIPEI_GETSTOP_URL, output_dir, 'stops.json')
        fetch_and_decompress(NEWTAIPEI_GETSTOPLOCATION_URL, output_dir, 'stop_locations.json')
        fetch_and_decompress(os.getenv("NEWTAIPEI_GETBUSROUTEFARELIST_URL"), output_dir, 'bus_route_fare_list.json')
    else:
        print(f"找不到 {args.city} 的資料來源。")

if __name__ == "__main__":
    main()