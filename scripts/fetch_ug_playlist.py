import json
import re
import sys
import html
import requests

def is_tab_item(obj):
    """
    Evaluates whether a dictionary represents a tab entry or wraps one.
    """
    if not isinstance(obj, dict):
        return False
    
    # Check if data is nested inside obj['tab']
    target = obj.get('tab') if isinstance(obj.get('tab'), dict) else obj
    
    # Core UG tab identifier keys
    tab_keys = {'song_name', 'songName', 'song_title', 'tab_url', 'tabUrl', 'artist_name', 'artistName', 'song_id', 'tab_id'}
    return any(k in target for k in tab_keys)

def find_tab_array(data):
    """
    Attempts direct schema navigation first, then falls back to recursive tree search.
    """
    if not isinstance(data, dict):
        return []

    # 1. Direct path navigation for standard UG page stores
    page_data = data.get('store', {}).get('page', {}).get('data', {})
    
    if isinstance(page_data, dict):
        candidate_containers = [
            page_data.get('playlist'),
            page_data.get('tabs'),
            page_data.get('list'),
            page_data.get('items'),
            page_data.get('page_data', {}).get('playlist') if isinstance(page_data.get('page_data'), dict) else None,
            page_data.get('plugin_data', {}).get('playlist') if isinstance(page_data.get('plugin_data'), dict) else None,
        ]

        for container in candidate_containers:
            if isinstance(container, list) and len(container) > 0 and is_tab_item(container[0]):
                return container
            elif isinstance(container, dict):
                for sub_key in ['tabs', 'items', 'list', 'songs']:
                    sub_list = container.get(sub_key)
                    if isinstance(sub_list, list) and len(sub_list) > 0 and is_tab_item(sub_list[0]):
                        return sub_list

    # 2. Fallback: Recursive search through the entire JSON object
    def recursive_search(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, list) and len(v) > 0:
                    if any(is_tab_item(item) for item in v[:5]):
                        return v
            for k, v in node.items():
                res = recursive_search(v)
                if res:
                    return res
        elif isinstance(node, list):
            for item in node:
                res = recursive_search(item)
                if res:
                    return res
        return []

    return recursive_search(data)

def parse_ug_json_payload(page_html):
    """
    Extracts embedded JSON state payload from UG HTML source using multiple fallbacks.
    """
    # Strategy 1: js-store data-content
    js_store_match = re.search(r'class=["\']js-store["\'][^>]*data-content=["\'](.*?)["\']', page_html, re.DOTALL)
    if not js_store_match:
        js_store_match = re.search(r'data-content=["\'](.*?)["\'][^>]*class=["\']js-store["\']', page_html, re.DOTALL)

    if js_store_match:
        try:
            raw_json = html.unescape(js_store_match.group(1))
            data = json.loads(raw_json)
            print("✅ Successfully extracted JSON from 'js-store' data-content element.", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ Failed parsing 'js-store' payload: {e}", flush=True)

    # Strategy 2: __NEXT_DATA__
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_html, re.DOTALL)
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            print("✅ Successfully extracted JSON from __NEXT_DATA__ script block.", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ Failed parsing __NEXT_DATA__ block: {e}", flush=True)

    # Strategy 3: window state variables
    win_store_match = re.search(r'window\.(?:UGAPP|__Store__|store)\s*=\s*(\{.*?\});\s*</script>', page_html, re.DOTALL)
    if win_store_match:
        try:
            data = json.loads(win_store_match.group(1))
            print("✅ Successfully extracted JSON from window state variable.", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ Failed parsing window state block: {e}", flush=True)

    print("❌ All JSON extraction strategies failed to locate embedded payload.", flush=True)
    return None

def fetch_ug_data():
    print("🚀 --- Starting Ultimate Guitar Sync Pipeline ---", flush=True)

    # 1. Read configuration strictly from root config.json
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("📄 Successfully read root config.json", flush=True)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not read config.json in root folder: {e}", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)

    ug_url = config.get('ugPlaylistUrl', '').strip()
    sheets_url = config.get('googleSheetsDeployUrl', '').strip()

    if not ug_url or not ug_url.startswith("http"):
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty or invalid in config.json.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)

    print(f"🎸 Fetching Ultimate Guitar tracks from: {ug_url}", flush=True)

    # 2. Fetch HTML source from Ultimate Guitar
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        resp = requests.get(ug_url, headers=headers, timeout=15)
        page_html = resp.text
        print(f"📄 Downloaded page source ({len(page_html)} bytes). Parsing...", flush=True)
    except Exception as e:
        print(f"❌ HTTP Fetch Error from Ultimate Guitar: {e}", flush=True)
        sys.exit(1)

    songs = []

    # 3. Parse JSON store and extract tabs
    payload = parse_ug_json_payload(page_html)

    if payload:
        raw_tabs = find_tab_array(payload)
        print(f"🔍 Extracted {len(raw_tabs)} raw tab entries from payload tree.", flush=True)

        for idx, item in enumerate(raw_tabs):
            if isinstance(item, dict):
                tab_data = item.get('tab') if isinstance(item.get('tab'), dict) else item
                
                song_title = (
                    tab_data.get('song_name') or 
                    tab_data.get('songName') or 
                    tab_data.get('song_title') or 
                    tab_data.get('title') or 
                    'Unknown Title'
                )
                
                artist_name = (
                    tab_data.get('artist_name') or 
                    tab_data.get('artistName') or 
                    tab_data.get('artist_title') or 
                    'Unknown Artist'
                )
                
                key_val = (
                    tab_data.get('tonality_name') or 
                    tab_data.get('tonalityName') or 
                    tab_data.get('key') or 
                    ''
                )
                
                tab_url = (
                    tab_data.get('tab_url') or 
                    tab_data.get('tabUrl') or 
                    tab_data.get('url') or 
                    tab_data.get('web_url') or 
                    ''
                )

                songs.append({
                    "id": idx + 1,
                    "title": song_title,
                    "artist": artist_name,
                    "key": key_val,
                    "ugUrl": tab_url
                })

    # 4. Write result to local playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Successfully written {len(songs)} songs to playlist.json.", flush=True)

    # 5. Push synchronized repertoire data to Google Sheets web app (if configured)
    if sheets_url and sheets_url.startswith("http"):
        print("📡 Syncing scraped repertoire with Google Sheets backend...", flush=True)
        try:
            sync_resp = requests.post(
                sheets_url,
                headers={'Content-Type': 'text/plain;charset=utf-8'},
                json={'action': 'syncPipelineSongs', 'songs': songs},
                timeout=15
            )
            print(f"✅ Google Sheets Sync Status Code: {sync_resp.status_code}", flush=True)
        except Exception as err:
            print(f"⚠️ Warning: Could not sync song order with Google Sheets: {err}", flush=True)

    print("🚀 Pipeline execution completed successfully!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
