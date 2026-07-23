document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('adminForm');
  const statusMsg = document.getElementById('statusMessage');

  // Load previously saved non-sensitive settings from localStorage
  if (localStorage.getItem('repoOwner')) document.getElementById('repoOwner').value = localStorage.getItem('repoOwner');
  if (localStorage.getItem('repoName')) document.getElementById('repoName').value = localStorage.getItem('repoName');
  if (localStorage.getItem('githubToken')) document.getElementById('githubToken').value = localStorage.getItem('githubToken');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    statusMsg.style.display = 'block';
    statusMsg.className = '';
    statusMsg.textContent = '⏳ Fetching current config.json from GitHub...';

    const token = document.getElementById('githubToken').value.trim();
    const owner = document.getElementById('repoOwner').value.trim();
    const repo = document.getElementById('repoName').value.trim();

    // Cache settings locally for quick reuse
    localStorage.setItem('repoOwner', owner);
    localStorage.setItem('repoName', repo);
    localStorage.setItem('githubToken', token);

    // Build the target payload object
    const newConfigData = {
      bandName: document.getElementById('bandName').value.trim(),
      bandMembers: document.getElementById('bandMembers').value.split(',').map(m => m.trim()),
      googleSheetsDeployUrl: document.getElementById('googleSheetsDeployUrl').value.trim(),
      ugPlaylistUrl: document.getElementById('ugPlaylistUrl').value.trim(),
      lastUpdated: new Date().toISOString()
    };

    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/contents/config.json`;

    try {
      // 1. Get current file sha (required by GitHub API to update an existing file)
      let sha = '';
      const getResponse = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (getResponse.ok) {
        const fileData = await getResponse.json();
        sha = fileData.sha;
      } else if (getResponse.status !== 404) {
        throw new Error(`GitHub API Returned ${getResponse.status}: ${getResponse.statusText}`);
      }

      // 2. Encode JSON string to base64 UTF-8 (GitHub API requirement)
      const jsonString = JSON.stringify(newConfigData, null, 2);
      const base64Content = btoa(unescape(encodeURIComponent(jsonString)));

      statusMsg.textContent = '⏳ Committing updated config.json to GitHub repository root...';

      // 3. Put request to commit updated config.json directly into repository root
      const putResponse = await fetch(apiUrl, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/vnd.github.v3+json'
        },
        body: JSON.stringify({
          message: 'admin(config): update root config.json via admin portal',
          content: base64Content,
          sha: sha || undefined
        })
      });

      if (putResponse.ok) {
        statusMsg.className = 'success';
        statusMsg.textContent = '✅ Success! config.json in root directory has been updated and committed to GitHub!';
      } else {
        const errData = await putResponse.json();
        throw new Error(errData.message || 'Failed to write config.json to GitHub');
      }

    } catch (error) {
      console.error('Save Error:', error);
      statusMsg.className = 'error';
      statusMsg.textContent = `❌ Error: ${error.message}`;
    }
  });
});    } catch (error) {
      console.error('Admin Submission Error:', error);
      statusMsg.textContent = `❌ Submission failed: ${error.message}`;
    }
  });
});
