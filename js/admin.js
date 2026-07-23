document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('adminForm');
  const downloadSection = document.getElementById('downloadSection');
  const downloadBtn = document.getElementById('downloadBtn');

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    // 1. Extract values from DOM
    const configData = {
      bandName: document.getElementById('bandName').value.trim(),
      bandMembers: document.getElementById('bandMembers').value.split(',').map(m => m.trim()),
      googleSheetsDeployUrl: document.getElementById('googleSheetsDeployUrl').value.trim(),
      ugPlaylistUrl: document.getElementById('ugPlaylistUrl').value.trim(),
      generatedAt: new Date().toISOString()
    };

    // 2. Format as human-readable JSON
    const jsonString = JSON.stringify(configData, null, 2);

    // 3. Construct an in-memory browser Blob
    const blob = new Blob([jsonString], { type: 'application/json' });
    const objectUrl = URL.createObjectURL(blob);

    // 4. Attach object URL to download button link
    downloadBtn.href = objectUrl;
    downloadSection.style.display = 'block';

    // Optional: Auto-scroll down to download button
    downloadSection.scrollIntoView({ behavior: 'smooth' });
  });
});
