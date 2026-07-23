import json
import re
import urllib.request
import sys

def get_latest_config():
    # 1. First, check local config.json for googleSheetsDeployUrl
    try:
        with open('config.json', 'r') as f:
            local_config = json.load(f)
    except Exception:
        local_config = {}

    sheets_url = local_config.get('googleSheetsDeployUrl')
    
    # 2. If Google Sheets URL exists, fetch live remote config entered via admin.html
    if sheets_url:
        try:
            print(f"📡 Fetching live config from Google Sheets: {sheets_url}?action=getConfig")
            req = urllib.request.Request(f"{sheets_url}?action=getConfig")
            with urllib.request.urlopen(req) as resp:
                remote_config = json.loads(resp.read().decode('utf-8'))
                if remote_config and remote_config.get('ugPlaylistUrl'):
                    print("✅ Successfully fetched live config from Google Sheets!")
                    # Merge and update local config.json file
                    local_config.update(remote_config)
                    with open('config.json', 'w') as f:
                        json.dump(local_config, f, indent=2)
                    return local_config
        except Exception as e:
            print(f"⚠️ Could not fetch from Google Sheets: {e}. Falling back to local config.json.")

    return local_config

# Rest of scraper execution stays identical...
