import json
import re
import sys
import requests

def extract_tabs_recursively(data):
    """
    Recursively searches the Next.js payload tree to find 
    the list of tabs regardless of UG's page schema variations.
    """
    if isinstance(data, dict):
        # Look for typical playlist/tab keys in UG's JSON payload
        for key in ['tabs', 'playlist', 'user_playlist', 'tabs_list']:
            if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                first_item = data[key][0]
                if isinstance(first_item, dict) and ('song_name' in first_item or 'songName' in first_item or 'tab_url' in first_item):
                    return data[key]
                elif isinstance(first_item, dict) and 'tabs' in first_item:
                    return extract_tabs_recursively(first_item)
        
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

def fetch_ug_data():
    print("🚀 --- Starting Ultimate Guitar Sync Pipeline ---", flush=True)

    # 1. Read ugPlaylistUrl strictly from root config.json
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("📄 Successfully read root config.json", flush=True)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not read config.json in root folder: {e}", flush=True)
        print("👉 Ensure admin.html was used to generate config.json and it is in the repository root.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)

    ug_url = config.get('ugPlaylistUrl', '').strip()

    # 2. Validate URL presence
    if not ug_url or not ug_url.startswith("http"):
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty or invalid in config.json.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)

    print(f"🎸 Fetching Ultimate Guitar tracks from: {ug_url}", flush=True)

    # 3. Request Ultimate Guitar Page Source
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        resp = requests.get(ug_url, headers=headers, timeout=15)
        html = resp.text
        print(f"📄 Downloaded page source ({len(html)} bytes). Extracting playlist data...", flush=True)
    except Exception as e:
        print(f"❌ HTTP Fetch Error from Ultimate Guitar: {e}", flush=True)
        sys.exit(1)

    songs = []

    # 4. Extract __NEXT_DATA__ script block and parse tabs
    next_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_match:
        try:
            data = json.loads(next_match.group(1))
            tabs = extract_tabs_recursively(data)
            print(f"🔍 Deep Search extracted {len(tabs)} tabs from Next.js payload.", flush=True)

            for idx, tab in enumerate(tabs):
                if isinstance(tab, dict):
                    song_title = tab.get('song_name') or tab.get('songName') or tab.get('song_title') or 'Unknown Title'
                    artist_name = tab.get('artist_name') or tab.get('artistName') or 'Unknown Artist'
                    key_val = tab.get('tonality_name') or tab.get('tonalityName') or tab.get('key') or ''
                    tab_url = tab.get('tab_url') or tab.get('tabUrl') or ''

                    songs.append({
                        "id": idx + 1,
                        "title": song_title,
                        "artist": artist_name,
                        "key": key_val,
                        "ugUrl": tab_url
                    })
        except Exception as err:
            print(f"⚠️ Error parsing Next.js JSON tree: {err}", flush=True)
    else:
        print("⚠️ Warning: Could not locate __NEXT_DATA__ script block in page HTML.", flush=True)

    # 5. Output result strictly to playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Successfully written {len(songs)} songs to playlist.json. Pipeline complete!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
