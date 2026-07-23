name: Daily Ultimate Guitar Sync

on:
  schedule:
    # Runs automatically at 00:00 UTC every day
    - cron: '0 0 * * *'
  # Enables the manual 'Run workflow' button in the GitHub Actions UI
  workflow_dispatch:

# Grants write permission so the bot can push updated playlist.json back to the repo
permissions:
  contents: write

jobs:
  sync-playlist:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python Environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Install Scraper Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      - name: Execute Ultimate Guitar Fetcher
        run: python scripts/fetch_ug_playlist.py

      - name: Commit and Push Updated Playlist
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          
          # Ensure target files exist so git add never fails
          [ -f config.json ] || echo "{}" > config.json
          [ -f playlist.json ] || echo "[]" > playlist.json
          
          git add config.json playlist.json
          
          # Only commit and push if differences are detected
          if ! git diff --staged --quiet; then
            git commit -m "build(cron): auto-sync Ultimate Guitar playlist"
            git push
          else
            echo "No changes detected in playlist.json. Skipping commit."
          fi
