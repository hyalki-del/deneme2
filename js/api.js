/**
 * API SERVICE LAYER
 * Handles all network requests to Google Apps Script (BaaS) and LRCLIB (Lyrics Engine)
 */

const ApiService = {
  
  /**
   * Fetch master playlist from Google Apps Script
   */
  async getPlaylist() {
    if (!BAND_CONFIG.googleScriptUrl) {
      console.warn("Google Script URL is not set in config.js");
      return [];
    }
    try {
      const response = await fetch(`${BAND_CONFIG.googleScriptUrl}?action=getPlaylist`);
      const result = await response.json();
      if (result.status === 'success') {
        return result.data;
      } else {
        throw new Error(result.message || 'Failed to load playlist');
      }
    } catch (err) {
      console.error("API Error [getPlaylist]:", err);
      throw err;
    }
  },

  /**
   * Send new playlist display order to Google Sheets
   * @param {Array<string>} songIdArray - Array of song IDs in the updated sequence
   */
  async updateOrder(songIdArray) {
    return this._post({
      action: 'updateOrder',
      playlist: songIdArray
    });
  },

  /**
   * Update the musical key of a specific song
   */
  async updateKey(songId, newKey) {
    return this._post({
      action: 'updateKey',
      songId: songId,
      newKey: newKey
    });
  },

  /**
   * Fetch lyrics from LRCLIB API with fallbacks
   */
  async fetchLyrics(title, artist) {
    // LRCLIB API Endpoint
    const getUrl = `https://lrclib.net/api/get?artist_name=${encodeURIComponent(artist)}&track_name=${encodeURIComponent(title)}`;
    
    try {
      const response = await fetch(getUrl, {
        headers: {
          'User-Agent': 'BandOpsApp/1.0 (https://github.com/band-app)'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return data.plainLyrics || data.syncedLyrics || "Plain lyrics not available for this track.";
      }
      
      // Fallback: Search endpoint if exact GET fails
      const searchUrl = `https://lrclib.net/api/search?track_name=${encodeURIComponent(title)}&artist_name=${encodeURIComponent(artist)}`;
      const searchRes = await fetch(searchUrl);
      if (searchRes.ok) {
        const searchData = await searchRes.json();
        if (searchData.length > 0) {
          return searchData[0].plainLyrics || searchData[0].syncedLyrics || "Lyrics found, but format is unreadable.";
        }
      }

      return "Lyrics not found in LRCLIB database.";
    } catch (err) {
      console.error("LRCLIB Fetch Error:", err);
      return "Network error while fetching lyrics. Please check your internet connection.";
    }
  },

  /**
   * Private POST helper for Google Apps Script
   */
  async _post(payload) {
    if (!BAND_CONFIG.googleScriptUrl) return;
    try {
      const response = await fetch(BAND_CONFIG.googleScriptUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' }, // Avoid CORS preflight flags on GAS
        body: JSON.stringify(payload)
      });
      return await response.json();
    } catch (err) {
      console.error("API POST Error:", err);
      throw err;
    }
  }
};
