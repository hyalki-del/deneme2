import os
import json
import re
import urllib.request
import sys

def fetch_ug_data():
    print("🚀 --- Starting Ultimate Guitar Fetcher ---", flush=True)

    # 1. Read secret from environment
    sheets_url = os.environ.get('GOOGLE_SHEETS_URL', '').strip()
    
    local_config = {}
    try:
        with open('config.json', 'r') as f:
            local_config = json.load(f)
    except Exception:
        pass

    ug_url = local_config.get('ugPlaylistUrl', '')

    # 2. Fetch live config from Google Sheets API
    if sheets_url and sheets_url.startswith("http"):
        endpoint = f"{sheets_url}?action=getConfig"
        print(f"📡 Querying Google Sheets Web App: {endpoint}", flush=True)
        try:
            req = urllib.request.Request(endpoint, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_data = resp.read().decode('utf-8')
                print(f"📥 Received response from Google Sheets API ({len(raw_data)} bytes).", flush=True)
                remote_config = json.loads(raw_data)
                
                if remote_config and remote_config.get('ugPlaylistUrl'):
                    ug_url = remote_config.get('ugPlaylistUrl')
                    print(f"✅ Retrieved live UG Playlist URL: {ug_url}", flush=True)
                    
                    # Update local config.json with current sheet data
                    local_config.update(remote_config)
                    local_config['googleSheetsDeployUrl'] = sheets_url
                    with open('config.json', 'w') as f:
                        json.dump(local_config, f, indent=2)
                else:
                    print("⚠️ Google Sheets responded, but 'ugPlaylistUrl' was empty inside the sheet.", flush=True)
        except Exception as e:
            print(f"❌ Failed to query Google Sheets API: {e}", flush=True)
    else:
        print("❌ CRITICAL ERROR: GOOGLE_SHEETS_URL secret is not configured in GitHub repository settings!", flush=True)

    # 3. Guard Clause: Abort if no valid UG link exists
    if not ug_url or not ug_url.startswith("http"):
        print("❌ CRITICAL ERROR: No valid Ultimate Guitar URL found. Writing empty array to playlist.json.", flush=True)
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(0)

    print(f"🎸 Scraping tracks from Ultimate Guitar: {ug_url}", flush=True)

    # 4. Fetch Ultimate Guitar Page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        req = urllib.request.Request(ug_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            print(f"📄 Successfully retrieved UG page source ({len(html)} bytes). Extracting tracks...", flush=True)
    except Exception as e:
        print(f"❌ HTTP Fetch Error from Ultimate Guitar: {e}", flush=True)
        sys.exit(1)

    songs = []

    # 5. Extract songs from Next.js payload
    next_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_match:
        try:
            data = json.loads(next_match.group(1))
            page_props = data.get('props', {}).get('pageProps', {})
            tabs = page_props.get('tabs', page_props.get('playlist', {}).get('tabs', []))
            print(f"🔍 Found {len(tabs)} tab items in __NEXT_DATA__ block.", flush=True)

            for idx, tab in enumerate(tabs):
                songs.append({
                    "id": idx + 1,
                    "title": tab.get('song_name', tab.get('songName', 'Unknown Title')),
                    "artist": tab.get('artist_name', tab.get('artistName', 'Unknown Artist')),
                    "key": tab.get('tonality_name', tab.get('tonalityName', '')),
                    "ugUrl": tab.get('tab_url', tab.get('tabUrl', ''))
                })
        except Exception as err:
            print(f"⚠️ Error parsing __NEXT_DATA__: {err}", flush=True)

    # 6. Save extracted tracks to root playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Written {len(songs)} songs to playlist.json. Pipeline completed successfully!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
