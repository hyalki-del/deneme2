import json
import re
import sys
import requests

def fetch_ug_data():
    print("🚀 --- Starting Ultimate Guitar Pipeline Sync ---", flush=True)

    # 1. Read root config.json created by admin.html generator
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("📄 Successfully loaded root config.json", flush=True)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not read config.json in root folder: {e}", flush=True)
        print("👉 Make sure you ran admin.html, downloaded config.json, and placed it in the repo root.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)

    sheets_url = config.get('googleSheetsDeployUrl', '').strip()
    ug_url = config.get('ugPlaylistUrl', '').strip()

    # 2. Check if live Google Sheets updates exist and sync if accessible
    if sheets_url and sheets_url.startswith("http"):
        endpoint = f"{sheets_url}?action=getConfig"
        print(f"📡 Querying Google Sheets for live overrides: {endpoint}", flush=True)
        try:
            resp = requests.get(endpoint, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True, timeout=15)
            if resp.status_code == 200:
                remote_config = resp.json()
                if remote_config and remote_config.get('ugPlaylistUrl'):
                    ug_url = remote_config.get('ugPlaylistUrl')
                    config.update(remote_config)
                    # Sync local file back
                    with open('config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"✅ Updated configuration from Google Sheets SSOT. Live UG URL: {ug_url}", flush=True)
        except Exception as err:
            print(f"⚠️ Could not pull remote overrides from Google Sheets ({err}). Using root config.json values.", flush=True)

    # 3. Validate UG URL presence
    if not ug_url or not ug_url.startswith("http"):
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty in config.json.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(0)

    print(f"🎸 Fetching Ultimate Guitar tracks from: {ug_url}", flush=True)

    # 4. Scrape Ultimate Guitar Page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        resp = requests.get(ug_url, headers=headers, timeout=15)
        html = resp.text
        print(f"📄 Downloaded page source ({len(html)} bytes). Extracting playlist data...", flush=True)
    except Exception as e:
        print(f"❌ HTTP Fetch Error from Ultimate Guitar: {e}", flush=True)
        sys.exit(1)

    songs = []

    # 5. Extract tab tracks from Next.js hydration payload
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

    # 6. Write playlist output file
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Written {len(songs)} songs to playlist.json. Pipeline finished successfully!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
