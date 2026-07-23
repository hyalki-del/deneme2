import json
import re
import urllib.request
import sys
from bs4 import BeautifulSoup

def fetch_ug_data():
    # 1. Read config.json
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Error: config.json not found in root directory.")
        sys.exit(1)

    ug_url = config.get('ugPlaylistUrl')
    if not ug_url:
        print("⚠️ Warning: ugPlaylistUrl is empty or missing in config.json. Writing empty array.")
        with open('playlist.json', 'w') as f:
            json.dump([], f)
        sys.exit(0)

    print(f"🔗 Target UG Playlist URL: {ug_url}")

    # Spoof full desktop Chrome browser header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache'
    }

    try:
        req = urllib.request.Request(ug_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"❌ HTTP Fetch Error: {e}")
        sys.exit(1)

    print(f"📄 Page fetched successfully ({len(html)} bytes). Extracting tracks...")
    songs = []

    # ----------------------------------------------------
    # STRATEGY A: Parse Next.js __NEXT_DATA__ script block
    # ----------------------------------------------------
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            page_props = data.get('props', {}).get('pageProps', {})
            
            # Find tab list inside nested keys
            tabs = page_props.get('tabs', page_props.get('playlist', {}).get('tabs', []))
            for idx, tab in enumerate(tabs):
                songs.append({
                    "id": idx + 1,
                    "title": tab.get('song_name', tab.get('songName', 'Unknown Title')),
                    "artist": tab.get('artist_name', tab.get('artistName', 'Unknown Artist')),
                    "key": tab.get('tonality_name', tab.get('tonalityName', '')),
                    "ugUrl": tab.get('tab_url', tab.get('tabUrl', ''))
                })
            if songs:
                print(f"✅ Strategy A (__NEXT_DATA__) succeeded! Found {len(songs)} songs.")
        except Exception as err:
            print(f"⚠️ Strategy A failed: {err}")

    # ----------------------------------------------------
    # STRATEGY B: Legacy window.UGAPP.store.page Regex
    # ----------------------------------------------------
    if not songs:
        ugapp_match = re.search(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', html, re.DOTALL)
        if ugapp_match:
            try:
                data = json.loads(ugapp_match.group(1))
                tabs = data.get('data', {}).get('tabs', [])
                for idx, tab in enumerate(tabs):
                    songs.append({
                        "id": idx + 1,
                        "title": tab.get('song_name', 'Unknown Title'),
                        "artist": tab.get('artist_name', 'Unknown Artist'),
                        "key": tab.get('tonality_name', ''),
                        "ugUrl": tab.get('tab_url', '')
                    })
                if songs:
                    print(f"✅ Strategy B (window.UGAPP) succeeded! Found {len(songs)} songs.")
            except Exception as err:
                print(f"⚠️ Strategy B failed: {err}")

    # ----------------------------------------------------
    # STRATEGY C: Pure DOM Parsing (Fallback)
    # ----------------------------------------------------
    if not songs:
        print("⚠️ Embedded JSON absent. Executing Strategy C (DOM Extraction)...")
        soup = BeautifulSoup(html, 'html.parser')
        tab_links = soup.select('a[href*="/tab/"]')
        
        seen_urls = set()
        for idx, link in enumerate(tab_links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if href and href not in seen_urls and text:
                seen_urls.add(href)
                # Attempt to split "Artist - Song" or format title cleanly
                parts = text.split(' - ')
                artist = parts[0] if len(parts) > 1 else 'Various'
                title = parts[1] if len(parts) > 1 else text
                
                songs.append({
                    "id": len(songs) + 1,
                    "title": title,
                    "artist": artist,
                    "key": "",
                    "ugUrl": href if href.startswith('http') else f"https://tabs.ultimate-guitar.com{href}"
                })
        if songs:
            print(f"✅ Strategy C (DOM Link Scraping) succeeded! Extracted {len(songs)} links.")

    # Save to playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Written {len(songs)} items to playlist.json.")

if __name__ == '__main__':
    fetch_ug_data()
