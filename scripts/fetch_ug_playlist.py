import json
import re
import sys
import html
import os
import requests

def is_tab_item(obj):
    if not isinstance(obj, dict):
        return False
    target = obj.get('tab') if isinstance(obj.get('tab'), dict) else obj
    tab_keys = {'song_name', 'songName', 'song_title', 'tab_url', 'tabUrl', 'artist_name', 'artistName', 'song_id', 'tab_id'}
    return any(k in target for k in tab_keys)

def find_tab_array(data):
    if not isinstance(data, dict):
        return []

    page_data = data.get('store', {}).get('page', {}).get('data', {})
    if isinstance(page_data, dict):
        candidate_containers = [
            page_data.get('playlist'),
            page_data.get('tabs'),
            page_data.get('list'),
            page_data.get('items')
        ]
        for container in candidate_containers:
            if isinstance(container, list) and len(container) > 0 and is_tab_item(container[0]):
                return container

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
    js_store_match = re.search(r'class=["\']js-store["\'][^>]*data-content=["\'](.*?)["\']', page_html, re.DOTALL)
    if js_store_match:
        try:
            return json.loads(html.unescape(js_store_match.group(1)))
        except:
            pass

    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_html, re.DOTALL)
    if next_data_match:
        try:
            return json.loads(next_data_match.group(1))
        except:
            pass

    return None

def sanitize_filename_part(text):
    """Sanitizes text for safe file system usage."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def fetch_lyrics_from_lrclib(song_title, artist_name):
    """Queries LRCLIB API for lyrics matching song title and artist."""
    url = f"https://lrclib.net/api/search?track_name={requests.utils.quote(song_title)}&artist_name={requests.utils.quote(artist_name)}"
    headers = {'User-Agent': 'BandRepertoireManager/1.0 (Educational Project)'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            results = resp.json()
            if isinstance(results, list) and len(results) > 0:
                # Prefer plain lyrics, fallback to synced lyrics if plain is empty
                match = results[0]
                lyrics = match.get('plainLyrics') or match.get('syncedLyrics')
                if lyrics:
                    return lyrics
    except Exception as e:
        print(f"⚠️ LRCLIB fetch warning for {song_title}: {e}", flush=True)
    return None

def fetch_ug_data():
    print("🚀 --- Starting Ultimate Guitar & LRCLIB Sync Pipeline ---", flush=True)

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not read config.json: {e}", flush=True)
        sys.exit(1)

    ug_url = config.get('ugPlaylistUrl', '').strip()
    sheets_url = config.get('googleSheetsDeployUrl', '').strip()

    if not ug_url:
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty.", flush=True)
        sys.exit(1)

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0.0.0 Safari/537.36'}
    try:
        resp = requests.get(ug_url, headers=headers, timeout=15)
        page_html = resp.text
    except Exception as e:
        print(f"❌ HTTP Fetch Error: {e}", flush=True)
        sys.exit(1)

    songs = []
    payload = parse_ug_json_payload(page_html)

    if payload:
        raw_tabs = find_tab_array(payload)
        for idx, item in enumerate(raw_tabs):
            if isinstance(item, dict):
                tab_data = item.get('tab') if isinstance(item.get('tab'), dict) else item
                songs.append({
                    "id": idx + 1,
                    "title": tab_data.get('song_name') or tab_data.get('songName') or tab_data.get('title') or 'Unknown Title',
                    "artist": tab_data.get('artist_name') or tab_data.get('artistName') or 'Unknown Artist',
                    "key": tab_data.get('tonality_name') or tab_data.get('tonalityName') or tab_data.get('key') or '',
                    "ugUrl": tab_data.get('tab_url') or tab_data.get('tabUrl') or tab_data.get('url') or ''
                })

    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"💾 Written {len(songs)} songs to playlist.json.", flush=True)

    # Create lyrics directory if it doesn't exist
    lyrics_dir = 'lyrics'
    os.makedirs(lyrics_dir, exist_ok=True)

    print("🎵 Downloading lyrics from LRCLIB...", flush=True)
    for song in songs:
        s_id = song['id']
        s_title = song['title']
        s_artist = song['artist']
        
        filename = f"{s_id}-{sanitize_filename_part(s_title)}-{sanitize_filename_part(s_artist)}.txt"
        filepath = os.path.join(lyrics_dir, filename)
        
        lyrics_text = fetch_lyrics_from_lrclib(s_title, s_artist)
        if lyrics_text:
            with open(filepath, 'w', encoding='utf-8') as lf:
                lf.write(lyrics_text)
            print(f"   [+] Saved lyrics: {filename}", flush=True)
        else:
            with open(filepath, 'w', encoding='utf-8') as lf:
                lf.write(f"--- Lyrics not found on LRCLIB for {s_title} by {s_artist} ---")
            print(f"   [!] Lyrics missing, placeholder created: {filename}", flush=True)

    if sheets_url and sheets_url.startswith("http"):
        print("📡 Syncing repertoire order with Google Sheets...", flush=True)
        try:
            requests.post(
                sheets_url,
                headers={'Content-Type': 'text/plain;charset=utf-8'},
                json={'action': 'syncPipelineSongs', 'songs': songs},
                timeout=15
            )
            print("✅ Google Sheets Sync Completed.", flush=True)
        except Exception as err:
            print(f"⚠️ Warning: Sheets sync failed: {err}", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
