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
        except Exception:
            pass

    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_html, re.DOTALL)
    if next_data_match:
        try:
            return json.loads(next_data_match.group(1))
        except Exception:
            pass

    return None

def sanitize_filename_part(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def fetch_lyrics_from_lrclib(song_title, artist_name):
    """Queries LRCLIB API safely with strict timeouts to prevent pipeline hangs."""
    url = f"https://lrclib.net/api/search?track_name={requests.utils.quote(song_title)}&artist_name={requests.utils.quote(artist_name)}"
    headers = {'User-Agent': 'BandRepertoireManager/1.0 (CI Pipeline)'}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            results = resp.json()
            if isinstance(results, list) and len(results) > 0:
                match = results[0]
                lyrics = match.get('plainLyrics') or match.get('syncedLyrics')
                if lyrics:
                    return lyrics
    except requests.exceptions.Timeout:
        print(f"⚠️ LRCLIB timeout for '{song_title} - {artist_name}'", flush=True)
    except Exception as e:
        print(f"⚠️ LRCLIB fetch warning for '{song_title}': {e}", flush=True)
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
        print("❌ CRITICAL ERROR: 'ugPlaylistUrl' is empty in config.json.", flush=True)
        sys.exit(1)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        print(f"🎸 Requesting Ultimate Guitar URL with 15s timeout...", flush=True)
        resp = requests.get(ug_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"❌ CRITICAL ERROR: Ultimate Guitar returned HTTP status {resp.status_code}", flush=True)
            sys.exit(1)
        page_html = resp.text
    except requests.exceptions.Timeout:
        print("❌ CRITICAL ERROR: Request to Ultimate Guitar timed out after 15 seconds.", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: HTTP Fetch Error from Ultimate Guitar: {e}", flush=True)
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

    print(f"💾 Successfully written {len(songs)} songs to playlist.json.", flush=True)

    # Safely handle lyrics directory generation
    lyrics_dir = 'lyrics'
    try:
        os.makedirs(lyrics_dir, exist_ok=True)
    except Exception as e:
        print(f"⚠️ Warning: Could not create lyrics directory: {e}", flush=True)

    print("🎵 Downloading lyrics from LRCLIB with strict timeouts...", flush=True)
    for song in songs:
        s_id = song['id']
        s_title = song['title']
        s_artist = song['artist']
        
        filename = f"{s_id}-{sanitize_filename_part(s_title)}-{sanitize_filename_part(s_artist)}.txt"
        filepath = os.path.join(lyrics_dir, filename)
        
        lyrics_text = fetch_lyrics_from_lrclib(s_title, s_artist)
        try:
            with open(filepath, 'w', encoding='utf-8') as lf:
                if lyrics_text:
                    lf.write(lyrics_text)
                    print(f"   [+] Saved lyrics: {filename}", flush=True)
                else:
                    lf.write(f"--- Lyrics not found on LRCLIB for {s_title} by {s_artist} ---")
                    print(f"   [!] Lyrics missing, placeholder created: {filename}", flush=True)
        except Exception as file_err:
            print(f"   [x] File write error for {filename}: {file_err}", flush=True)

    # Sync with Google Sheets with a strict timeout guard
    if sheets_url and sheets_url.startswith("http"):
        print("📡 Syncing repertoire order with Google Sheets...", flush=True)
        try:
            sync_resp = requests.post(
                sheets_url,
                headers={'Content-Type': 'text/plain;charset=utf-8'},
                json={'action': 'syncPipelineSongs', 'songs': songs},
                timeout=12
            )
            print(f"✅ Google Sheets Sync Completed (Status: {sync_resp.status_code}).", flush=True)
        except requests.exceptions.Timeout:
            print("⚠️ Warning: Google Sheets sync request timed out. Pipeline proceeding.", flush=True)
        except Exception as err:
            print(f"⚠️ Warning: Sheets sync failed: {err}", flush=True)

    print("🚀 Pipeline execution completed successfully!", flush=True)

if __name__ == '__main__':
    fetch_ug_data()
