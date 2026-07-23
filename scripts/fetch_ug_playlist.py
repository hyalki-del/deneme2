import json
import re
import urllib.request
from bs4 import BeautifulSoup

def fetch_ug_data():
    # 1. Read configuration from root config.json
    with open('config.json', 'r') as f:
        config = json.load(f)

    ug_url = config.get('ugPlaylistUrl')
    if not ug_url:
        print("No UG playlist URL configured.")
        return

    # 2. Fetch HTML content from Ultimate Guitar link
    req = urllib.request.Request(
        ug_url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    
    html = urllib.request.urlopen(req).read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # 3. Ultimate Guitar stores structured store data inside window.UGAPP.store.page
    songs = []
    store_script = soup.find('script', text=re.compile(r'window\.UGAPP\.store\.page'))

    if store_script:
        json_text = re.search(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', store_script.string)
        if json_text:
            data = json.loads(json_text.group(1))
            # Extract tab list items
            tabs = data.get('data', {}).get('tabs', [])
            for idx, tab in enumerate(tabs):
                songs.append({
                    "id": idx + 1,
                    "title": tab.get('song_name', 'Unknown Title'),
                    "artist": tab.get('artist_name', 'Unknown Artist'),
                    "key": tab.get('tonality_name', ''),
                    "ugUrl": tab.get('tab_url', '')
                })

    # 4. Save parsed songs directly into root playlist.json
    with open('playlist.json', 'w') as f:
        json.dump(songs, f, indent=2)

    print(f"Successfully fetched {len(songs)} songs from UG and updated playlist.json.")

if __name__ == '__main__':
    fetch_ug_data()
