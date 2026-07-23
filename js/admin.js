document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('adminForm');
  const statusMsg = document.getElementById('statusMessage');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    statusMsg.textContent = '⏳ Saving configuration to Google Sheets...';

    // 1. Construct payload from admin form
    const configData = {
      bandName: document.getElementById('bandName').value.trim(),
      bandMembers: document.getElementById('bandMembers').value.split(',').map(m => m.trim()),
      bandPhotos: document.getElementById('bandPhotos').value ? document.getElementById('bandPhotos').value.split(',').map(p => p.trim()) : [],
      googleSheetsDeployUrl: document.getElementById('googleSheetsDeployUrl').value.trim(),
      ugPlaylistUrl: document.getElementById('ugPlaylistUrl').value.trim(),
      lastUpdated: new Date().toISOString()
    };

    try {
      // 2. Post configuration directly to Google Apps Script Web App
      const response = await fetch(configData.googleSheetsDeployUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' }, // Avoids CORS preflight issue in Google Apps Script
        body: JSON.stringify({
          action: 'saveConfig',
          config: configData
        })
      });

      const result = await response.json();

      if (result.status === 'success') {
        statusMsg.textContent = '✅ Config saved successfully! You can now run the GitHub Action or wait for the auto-sync.';
      } else {
        throw new Error(result.message || 'Error saving configuration.');
      }
    } catch (error) {
      console.error('Admin Submission Error:', error);
      statusMsg.textContent = `❌ Submission failed: ${error.message}`;
    }
  });
});
