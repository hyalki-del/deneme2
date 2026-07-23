/**
 * @file core/app.js
 * @description Central Architecture Engine & State Bootstrapper for Serverless Dashboard.
 */

class BandDashboardEngine {
  constructor() {
    this.config = null;
    this.keyOverrides = null;
    this.currentImageIndex = 0;
    this.bgElement = null;
    
    // Chromatic Scale Reference Array (ISO Standard Notation)
    this.chromaticScale = [
      'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
    ];
  }

  /**
   * Application entry point. Loads configuration and executes render pipeline.
   */
  async init() {
    try {
      // Parallel fetch for core JSON datasets with cache busting
      const cacheBuster = `?v=${Date.now()}`;
      const [configRes, overridesRes] = await Promise.all([
        fetch(`./config.json${cacheBuster}`),
        fetch(`./key-overrides.json${cacheBuster}`).catch(() => null)
      ]);

      if (!configRes.ok) {
        throw new Error(`Config HTTP error! status: ${configRes.status}`);
      }

      this.config = await configRes.json();
      if (overridesRes && overridesRes.ok) {
        this.keyOverrides = await overridesRes.json();
      }

      // Execute Initialization Sequence
      this.applyThemeVariables();
      this.renderBrandHeader();
      this.renderMarquee();
      this.renderNavigation();
      this.setupHeroCarousel();

    } catch (error) {
      console.error('[Engine Core] Initialization Failed:', error);
    }
  }

  /**
   * Dynamic CSS Variable Injection Engine.
   */
  applyThemeVariables() {
    if (!this.config?.theme) return;

    const root = document.documentElement;
    const { theme } = this.config;

    if (theme.accentColor) root.style.setProperty('--accent-color', theme.accentColor);
    if (theme.accentGlow)  root.style.setProperty('--accent-glow', theme.accentGlow);
    if (theme.bgDark)      root.style.setProperty('--bg-dark', theme.bgDark);
    if (theme.surfaceDark) root.style.setProperty('--surface-dark', theme.surfaceDark);
    if (theme.borderColor) root.style.setProperty('--border-color', theme.borderColor);
  }

  /**
   * Renders Brand Logo and Title in Navigation Bar.
   */
  renderBrandHeader() {
    const brandLogo = document.getElementById('brandLogo');
    if (brandLogo && this.config?.band?.shortName) {
      brandLogo.textContent = this.config.band.shortName;
    }
  }

  /**
   * Populates hardware-accelerated continuous LED marquee display.
   */
  renderMarquee() {
    const track = document.getElementById('marqueeTrack');
    if (!track || !this.config?.marqueeMessages) return;

    const messagesHtml = this.config.marqueeMessages
      .map(msg => `<span><i class="fa-solid fa-bolt"></i> ${this.escapeHtml(msg)}</span>`)
      .join('');

    // Duplicate string payload for seamless 100% loop keyframe transition
    track.innerHTML = `
      <div class="led-content">${messagesHtml}</div>
      <div class="led-content" aria-hidden="true">${messagesHtml}</div>
    `;
  }

  /**
   * Renders action navigation cards into responsive grid.
   */
  renderNavigation() {
    const grid = document.getElementById('navigationGrid');
    if (!grid || !this.config?.navigation) return;

    grid.innerHTML = this.config.navigation.map(nav => `
      <a href="${nav.url}" class="nav-card" id="nav-${nav.id}">
        <i class="${nav.icon}"></i>
        <h3>${this.escapeHtml(nav.label)}</h3>
        <p>${this.escapeHtml(nav.description)}</p>
      </a>
    `).join('');
  }

  /**
   * Asynchronous image carousel with preloading and micro-flicker transitions.
   */
  setupHeroCarousel() {
    const images = this.config?.assets?.heroImages || [];
    if (images.length === 0) return;

    // Asynchronous asset preloading to prevent render lag
    images.forEach(src => {
      const img = new Image();
      img.src = src;
    });

    this.bgElement = document.getElementById('heroBg');
    if (!this.bgElement) return;

    // Set initial image
    this.bgElement.style.backgroundImage = `url('${images[0]}')`;

    // Stage light bulb flicker interval cycle
    setInterval(() => {
      this.bgElement.classList.add('bulb-buzz');

      setTimeout(() => {
        this.currentImageIndex = (this.currentImageIndex + 1) % images.length;
        this.bgElement.style.backgroundImage = `url('${images[this.currentImageIndex]}')`;
      }, 180);

      setTimeout(() => {
        this.bgElement.classList.remove('bulb-buzz');
      }, 450);
    }, 4500);
  }

  /**
   * Global Music Theory Helper: Transposes root chord key by semitone offset.
   * @param {string} chord - Original root note (e.g., "Am", "G#m", "C")
   * @param {number} offset - Semitone transposition delta
   * @returns {string} Transposed chord string
   */
  transposeChord(chord, offset) {
    if (!chord) return '';
    const match = chord.match(/^([A-G][#b]?)(.*)/);
    if (!match) return chord;

    let [, root, quality] = match;
    
    // Standardize flat notes to enharmonic sharp equivalents
    const flatToSharpMap = { 'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#' };
    root = flatToSharpMap[root] || root;

    const originalIdx = this.chromaticScale.indexOf(root);
    if (originalIdx === -1) return chord;

    // Modular Arithmetic over Z_12
    const transposedIdx = (originalIdx + offset % 12 + 12) % 12;
    return this.chromaticScale[transposedIdx] + quality;
  }

  /**
   * Utility to sanitize HTML strings against cross-site scripting (XSS).
   */
  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Instantiate Singleton Core Application Engine on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.AppEngine = new BandDashboardEngine();
  window.AppEngine.init();
});
