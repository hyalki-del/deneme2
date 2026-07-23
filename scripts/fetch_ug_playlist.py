import json
import re
import sys
import html
import requests

def extract_tabs_recursively(data):
    """
    Recursively searches the JSON object tree to find 
    the list of tabs regardless of UG's page schema variations.
    """
    if isinstance(data, dict):
        # Check standard playlist/tab keys in UG JSON schemas
        for key in ['tabs', 'playlist', 'user_playlist', 'tabs_list', 'songbook']:
            if key in data:
                val = data[key]
                if isinstance(val, list) and len(val) > 0:
                    first_item = val[0]
                    if isinstance(first_item, dict) and ('song_name' in first_item or 'songName' in first_item or 'tab_url' in first_item or 'tab' in first_item):
                        return val
                elif isinstance(val, dict) and 'tabs' in val:
                    return extract_tabs_recursively(val['tabs'])

        # Recurse through dictionary values
        for k, v in data.items():
            result = extract_tabs_recursively(v)
            if result:
                return result

    elif isinstance(data, list):
        for item in data:
            result = extract_tabs_recursively(item)
            if result:
                return result

    return []

def parse_ug_json_payload(page_html):
    """
    Extracts and parses UG's embedded JSON payload using 3 fallback strategies.
    """
    # Strategy 1: Search for class="js-store" data-content="..."
    js_store_match = re.search(r'class=["\']js-store["\'][^>]*data-content=["\'](.*?)["\']', page_html, re.DOTALL)
    if not js_store_match:
        # Alt regex order (data-content before class)
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

    # Strategy 3: Search for window.UGAPP = ... or window.__Store__ = ...
    win_store_match = re.search(r'window\.(?:UGAPP|__Store__|store)\s*=\s*(\{.*?\});\s*</script>', page_html, re.DOTALL)
    if win_store_match:
        try:
            data = json.loads(win_store_match.group(1))
            print("✅ Successfully extracted JSON from window state variable.", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ Failed parsing window state block: {e}", flush=True)

    print("❌ All JSON extraction strategies failed to find embedded payload.", flush=True)
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

    # 3. Parse JSON store using fallbacks
    payload = parse_ug_json_payload(page_html)

    if payload:
        raw_tabs = extract_tabs_recursively(payload)
        print(f"🔍 Extracted {len(raw_tabs)} raw tab entries from payload.", flush=True)

        for idx, item in enumerate(raw_tabs):
            if isinstance(item, dict):
                # Handle nested item['tab'] structure or direct tab dict
                tab_data = item.get('tab', item)
                
                song_title = tab_data.get('song_name') or tab_data.get('songName') or tab_data.get('song_title') or 'Unknown Title'
                artist_name = tab_data.get('artist_name') or tab_data.get('artistName') or 'Unknown Artist'
                key_val = tab_data.get('tonality_name') or tab_data.get('tonalityName') or tab_data.get('key') or ''
                tab_url = tab_data.get('tab_url') or tab_data.get('tabUrl') or ''

                songs.append({
                    "id": idx + 1,
                    "title": song_title,
                    "artist": artist_name,
                    "key": key_val,
                    "ugUrl": tab_url
                })

    # 4. Save result
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Successfully written {len(songs)} songs to playlist.json. Pipeline complete!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
