/**
 * Admin Processing Logic
 * Collects form inputs, fetches UG Playlist via server-side scraper,
 * and pushes state straight to Google Sheets.
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('admin-form');
  const statusMsg = document.getElementById('status-message');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    statusMsg.textContent = '🔄 Pushing settings to Google Sheets & parsing UG playlist...';

    const bandData = {
      bandName: document.getElementById('band-name').value.trim(),
      bandMembers: document.getElementById('band-members').value.split(',').map(m => m.trim()),
      bandLogoUrl: document.getElementById('band-logo-url').value.trim(),
      bandPhotosUrls: document.getElementById('band-photos-urls').value.trim().split(','),
      sheetsUrl: document.getElementById('sheets-url').value.trim(),
      ugLink: document.getElementById('ug-link').value.trim(),
      updatedAt: new Date().toISOString()
    };

    try {
      // 1. Extract Ultimate Guitar Playlist songs using our central API service
      const fetchedSongs = await API.fetchUGPlaylist(bandData.ugLink);

      // 2. Transmit config & parsed songs directly to Google Sheets Web App endpoint
      const response = await fetch(bandData.sheetsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' }, // Apps Script CORS workaround
        body: JSON.stringify({
          action: 'saveConfig',
          config: bandData,
          songs: fetchedSongs
        })
      });

      const result = await response.json();

      if (result.status === 'success') {
        statusMsg.textContent = '✅ Setup synced to Google Sheets successfully!';
        setTimeout(() => {
          window.location.href = 'playlist.html';
        }, 1500);
      } else {
        throw new Error(result.message || 'Error writing to Google Sheets');
      }

    } catch (error) {
      console.error('Admin submit error:', error);
      statusMsg.textContent = `❌ Setup failed: ${error.message}`;
    }
  });
});
