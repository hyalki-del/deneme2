import json
import re
import sys
import html
import requests

def is_tab_object(obj):
    """
    Checks if a dictionary represents a tab or contains a nested tab object.
    """
    if not isinstance(obj, dict):
        return False
    
    # Check if 'tab' is a nested dictionary inside the item wrapper
    target = obj.get('tab') if isinstance(obj.get('tab'), dict) else obj
    
    # Core identifying attributes of an Ultimate Guitar tab entry
    has_title = any(k in target for k in ['song_name', 'songName', 'song_title', 'title'])
    has_url = any(k in target for k in ['tab_url', 'tabUrl', 'url', 'web_url'])
    has_artist = any(k in target for k in ['artist_name', 'artistName', 'artist_title'])
    
    return (has_title and has_url) or (has_title and has_artist)

def find_all_tab_arrays(data):
    """
    Recursively explores every node in the JSON tree and returns 
    the first array where items represent valid tab objects.
    """
    if isinstance(data, dict):
        # 1. Check all lists directly attached to this dictionary
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                # Test first few items to confirm it's a tab list
                if any(is_tab_object(item) for item in value[:3]):
                    return value
        
        # 2. Recurse deeper into nested dictionaries
        for key, value in data.items():
            result = find_all_tab_arrays(value)
            if result:
                return result

    elif isinstance(data, list):
        # If we encounter a list of lists/dicts, recurse into items
        for item in data:
            result = find_all_tab_arrays(item)
            if result:
                return result

    return []

def parse_ug_json_payload(page_html):
    """
    Extracts and parses UG's embedded JSON payload using multi-fallback strategy.
    """
    # Strategy 1: Search for class="js-store" data-content="..."
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

    # Strategy 2: Search for <script id="__NEXT_DATA__">
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_html, re.DOTALL)
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            print("✅ Successfully extracted JSON from __NEXT_DATA__ script block.", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ Failed parsing __NEXT_DATA__ block: {e}", flush=True)

    # Strategy 3: Search for window.UGAPP or window.__Store__
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

    # 1. Read ugPlaylistUrl strictly from root config.json
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
        raw_tabs = find_all_tab_arrays(payload)
        print(f"🔍 Extracted {len(raw_tabs)} raw tab entries from payload tree.", flush=True)

        for idx, item in enumerate(raw_tabs):
            if isinstance(item, dict):
                # Handle wrapper objects where tab info lives under item['tab']
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

    # 4. Write result
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Successfully written {len(songs)} songs to playlist.json. Pipeline complete!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
