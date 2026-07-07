// Section 11.2 — graphics tier auto-detection + always-visible manual override.
//   WebGL2 + width > 1024px + non-'slow-2g'  -> Tier 1
//   WebGL1-only or mid-range                 -> Tier 2
//   no WebGL / explicit low-end              -> Tier 3
const OVERRIDE_KEY = "tdl_tier_override";

function webglSupport() {
  const canvas = document.createElement("canvas");
  if (canvas.getContext("webgl2")) return 2;
  if (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")) return 1;
  return 0;
}

export function detectTier() {
  const gl = webglSupport();
  const conn = navigator.connection || {};
  const type = conn.effectiveType || "";
  const slow = type === "slow-2g" || type === "2g";
  if (gl === 2 && window.screen.width > 1024 && type !== "slow-2g") return 1;
  if (gl >= 1 && !slow) return 2;
  return 3;
}

export function activeTier() {
  const override = localStorage.getItem(OVERRIDE_KEY);
  if (override && ["1", "2", "3"].includes(override)) return parseInt(override, 10);
  return detectTier();
}

export function setTierOverride(value, onChange) {
  if (value === "auto") localStorage.removeItem(OVERRIDE_KEY);
  else localStorage.setItem(OVERRIDE_KEY, String(value));
  onChange(activeTier());
}

export function initTierControl(selectEl, onChange) {
  const override = localStorage.getItem(OVERRIDE_KEY);
  selectEl.value = override || "auto";
  selectEl.addEventListener("change", () => setTierOverride(selectEl.value, onChange));
  return activeTier();
}
