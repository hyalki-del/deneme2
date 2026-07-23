import json
import re
import sys
import requests

def fetch_ug_data():
    print("🚀 --- Reading config.json from Repository Root ---", flush=True)

    # 1. Read config.json from root directory
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("📄 Read root config.json successfully.", flush=True)
    except Exception as e:
        print(f"❌ Error reading config.json: {e}", flush=True)
        config = {}

    ug_url = config.get('ugPlaylistUrl', '').strip()

    # 2. Guard clause
    if not ug_url or not ug_url.startswith("http"):
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty inside root config.json.", flush=True)
        print("👉 Please fill out admin.html to update config.json.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(0)

    print(f"🎸 Fetching Ultimate Guitar tracks from: {ug_url}", flush=True)

    # 3. Scrape Ultimate Guitar
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        resp = requests.get(ug_url, headers=headers, timeout=15)
        html = resp.text
        print(f"📄 Downloaded page source ({len(html)} bytes). Parsing...", flush=True)
    except Exception as e:
        print(f"❌ HTTP Fetch Error: {e}", flush=True)
        sys.exit(1)

    songs = []

    # 4. Extract songs from Next.js payload
    next_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_match:
        try:
            data = json.loads(next_match.group(1))
            page_props = data.get('props', {}).get('pageProps', {})
            tabs = page_props.get('tabs', page_props.get('playlist', {}).get('tabs', []))
            print(f"🔍 Found {len(tabs)} tabs in payload.", flush=True)

            for idx, tab in enumerate(tabs):
                songs.append({
                    "id": idx + 1,
                    "title": tab.get('song_name', tab.get('songName', 'Unknown Title')),
                    "artist": tab.get('artist_name', tab.get('artistName', 'Unknown Artist')),
                    "key": tab.get('tonality_name', tab.get('tonalityName', '')),
                    "ugUrl": tab.get('tab_url', tab.get('tabUrl', ''))
                })
        except Exception as err:
            print(f"⚠️ Error parsing Next.js payload: {err}", flush=True)

    # 5. Write extracted songs to playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Successfully written {len(songs)} songs to playlist.json!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
