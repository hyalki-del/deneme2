/**
 * DECOUPLED API SERVICE LAYER (STATIC DATA + BACKGROUND SYNC)
 */

const ApiService = {
  
  /**
   * Fetch master playlist from pre-built static JSON file (instant load)
   */
  async getPlaylist() {
    try {
      // First attempt to load static background-synced JSON asset
      const response = await fetch('data/playlist.json');
      if (response.ok) {
        const result = await response.json();
        return result.data || result;
      }
      throw new Error("Static playlist.json not found, attempting fallback...");
    } catch (err) {
      console.warn("Static JSON fetch failed. Attempting live fallback...", err);
      // Fallback to live Google Apps Script endpoint if static file is missing
      if (BAND_CONFIG.googleScriptUrl) {
        const liveRes = await fetch(`${BAND_CONFIG.googleScriptUrl}?action=getPlaylist`);
        const liveJson = await liveRes.json();
        return liveJson.data || [];
      }
      return [];
    }
  },

  /**
   * Fetch calendar events from static JSON file
   */
  async getCalendar() {
    try {
      const response = await fetch('data/calendar.json');
      if (response.ok) {
        const result = await response.json();
        return result.data || result;
      }
      throw new Error("Static calendar.json not found");
    } catch (err) {
      if (BAND_CONFIG.googleScriptUrl) {
        const liveRes = await fetch(`${BAND_CONFIG.googleScriptUrl}?action=getCalendar`);
        const liveJson = await liveRes.json();
        return liveJson.data || [];
      }
      return [];
    }
  },

  /**
   * Send new playlist display order to Google Sheets
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
    const getUrl = `https://lrclib.net/api/get?artist_name=${encodeURIComponent(artist)}&track_name=${encodeURIComponent(title)}`;
    try {
      const response = await fetch(getUrl, {
        headers: { 'User-Agent': 'BandOpsApp/1.0 (https://github.com/band-app)' }
      });

      if (response.ok) {
        const data = await response.json();
        return data.plainLyrics || data.syncedLyrics || "Plain lyrics not available for this track.";
      }
      return "Lyrics not found in LRCLIB database.";
    } catch (err) {
      return "Network error while fetching lyrics.";
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
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify(payload)
      });
      return await response.json();
    } catch (err) {
      console.error("API POST Error:", err);
      throw err;
    }
  }
};
