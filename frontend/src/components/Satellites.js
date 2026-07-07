// v3 §10.2 — satellite overlay: client-side orbital propagation from TLE
// data (fetched daily by the backend from CelesTrak, served via
// /api/satellites).
//
// Zero-dependency simplification, documented per CLAUDE.md: instead of a
// full SGP4 implementation this uses two-body circular-orbit propagation
// from the TLE's mean motion, inclination, RAAN and mean anomaly, plus
// Earth rotation (GMST). Positionally approximate (km-scale drift over
// hours), which is fine for an aesthetic/informational moving-dot layer —
// it is "purely an aesthetic layer, not correlated with any other data".
const MU = 398600.4418;         // km^3/s^2
const EARTH_RADIUS = 6371.0;
const OMEGA_EARTH = 7.2921159e-5; // rad/s

function parseTle(l1, l2) {
  return {
    epochYear: parseInt(l1.slice(18, 20), 10),
    epochDay: parseFloat(l1.slice(20, 32)),
    inclination: parseFloat(l2.slice(8, 16)) * Math.PI / 180,
    raan: parseFloat(l2.slice(17, 25)) * Math.PI / 180,
    meanAnomaly: parseFloat(l2.slice(43, 51)) * Math.PI / 180,
    meanMotion: parseFloat(l2.slice(52, 63)),   // rev/day
  };
}

function epochToDate(year2, day) {
  const year = year2 < 57 ? 2000 + year2 : 1900 + year2;
  return new Date(Date.UTC(year, 0, 1) + (day - 1) * 86400000);
}

function gmst(date) {
  const jd = date.getTime() / 86400000 + 2440587.5;
  const t = (jd - 2451545.0) / 36525.0;
  let g = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t;
  return ((g % 360) + 360) % 360 * Math.PI / 180;
}

export function propagate(sat, date = new Date()) {
  const tle = sat._parsed || (sat._parsed = parseTle(sat.l1, sat.l2));
  const n = tle.meanMotion * 2 * Math.PI / 86400;        // rad/s
  const a = Math.cbrt(MU / (n * n));                     // semi-major axis km
  const dt = (date - epochToDate(tle.epochYear, tle.epochDay)) / 1000;
  const M = tle.meanAnomaly + n * dt;                    // circular: ν ≈ M
  // position in orbital plane -> ECI
  const cosM = Math.cos(M), sinM = Math.sin(M);
  const cosR = Math.cos(tle.raan), sinR = Math.sin(tle.raan);
  const cosI = Math.cos(tle.inclination), sinI = Math.sin(tle.inclination);
  const xEci = a * (cosR * cosM - sinR * sinM * cosI);
  const yEci = a * (sinR * cosM + cosR * sinM * cosI);
  const zEci = a * (sinM * sinI);
  // ECI -> ECEF via GMST
  const g = gmst(date);
  const x = Math.cos(g) * xEci + Math.sin(g) * yEci;
  const y = -Math.sin(g) * xEci + Math.cos(g) * yEci;
  const z = zEci;
  const r = Math.hypot(x, y, z);
  return {
    name: sat.name,
    lat: Math.asin(z / r) * 180 / Math.PI,
    lon: Math.atan2(y, x) * 180 / Math.PI,
    altKm: r - EARTH_RADIUS,
  };
}

export function propagateAll(satellites, date = new Date()) {
  const out = [];
  for (const sat of satellites) {
    try {
      const p = propagate(sat, date);
      if (isFinite(p.lat) && isFinite(p.lon) && p.altKm > 100 && p.altKm < 45000) {
        out.push(p);
      }
    } catch { /* malformed TLE line — skip */ }
  }
  return out;
}
