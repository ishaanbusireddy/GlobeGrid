// Graphics tier auto-detection (Section 11.2) + manual override persistence.
// Auto-detect is a default, not a lock — the override control in App.jsx is
// always visible regardless of the detected tier.

const OVERRIDE_KEY = 'globegrid.tierOverride';

function webglSupport() {
  try {
    const canvas = document.createElement('canvas');
    if (canvas.getContext('webgl2')) return 2;
    if (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')) return 1;
    return 0;
  } catch {
    return 0;
  }
}

export function detectTier() {
  const gl = webglSupport();
  const wideScreen = window.innerWidth > 1024;
  const connection = navigator.connection?.effectiveType ?? 'unknown';
  const slowConnection = connection === 'slow-2g' || connection === '2g';

  // WebGL2 + screen width > 1024px + non-'slow-2g' connection -> Tier 1.
  if (gl === 2 && wideScreen && !slowConnection) return 1;
  // WebGL1-only or mid-range signals -> Tier 2.
  if (gl >= 1) return 2;
  // No WebGL or explicit low-end signal -> Tier 3.
  return 3;
}

export function getTierOverride() {
  const saved = localStorage.getItem(OVERRIDE_KEY);
  return saved ? Number(saved) : null;
}

export function setTierOverride(tier) {
  if (tier === null) localStorage.removeItem(OVERRIDE_KEY);
  else localStorage.setItem(OVERRIDE_KEY, String(tier));
}

export function resolveTier() {
  return getTierOverride() ?? detectTier();
}
