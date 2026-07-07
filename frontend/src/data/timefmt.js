// v6.1.1 — timezone + date settings. A user-chosen IANA zone (persisted) is
// applied to every rendered timestamp via Intl.DateTimeFormat. "Local" uses
// the browser default; the list spans the US, Europe, Asia and the rest of
// the major inhabited zones.

const TZ_KEY = "tdl_timezone";
const DATEFMT_KEY = "tdl_datefmt";   // "iso" | "us" | "eu"

export const TIMEZONES = [
  { group: "General", zones: [
    ["", "Local (device)"], ["UTC", "UTC"] ] },
  { group: "United States", zones: [
    ["America/New_York", "Eastern (New York)"], ["America/Chicago", "Central (Chicago)"],
    ["America/Denver", "Mountain (Denver)"], ["America/Los_Angeles", "Pacific (Los Angeles)"],
    ["America/Anchorage", "Alaska"], ["Pacific/Honolulu", "Hawaii"] ] },
  { group: "Americas", zones: [
    ["America/Sao_Paulo", "Brazil (São Paulo)"], ["America/Mexico_City", "Mexico City"],
    ["America/Bogota", "Colombia/Peru"], ["America/Argentina/Buenos_Aires", "Argentina"] ] },
  { group: "Europe / Africa", zones: [
    ["Europe/London", "UK / Ireland (London)"], ["Europe/Paris", "Central Europe (Paris)"],
    ["Europe/Athens", "Eastern Europe (Athens)"], ["Europe/Moscow", "Moscow"],
    ["Africa/Cairo", "Cairo"], ["Africa/Johannesburg", "South Africa"],
    ["Africa/Lagos", "West Africa (Lagos)"] ] },
  { group: "Middle East / Asia", zones: [
    ["Asia/Jerusalem", "Israel (Jerusalem)"], ["Asia/Dubai", "Gulf (Dubai)"],
    ["Asia/Tehran", "Iran (Tehran)"], ["Asia/Karachi", "Pakistan"],
    ["Asia/Kolkata", "India"], ["Asia/Dhaka", "Bangladesh"], ["Asia/Bangkok", "Thailand/Vietnam"],
    ["Asia/Shanghai", "China"], ["Asia/Tokyo", "Japan"], ["Asia/Seoul", "Korea"],
    ["Asia/Singapore", "Singapore/Malaysia"] ] },
  { group: "Oceania", zones: [
    ["Australia/Sydney", "Australia (Sydney)"], ["Pacific/Auckland", "New Zealand"] ] },
];

let _tz = localStorage.getItem(TZ_KEY) || "";
let _dateFmt = localStorage.getItem(DATEFMT_KEY) || "iso";

export function getTimeZone() { return _tz; }
export function getDateFormat() { return _dateFmt; }
export function setTimeZone(tz) { _tz = tz || ""; localStorage.setItem(TZ_KEY, _tz); }
export function setDateFormat(f) { _dateFmt = f || "iso"; localStorage.setItem(DATEFMT_KEY, _dateFmt); }

function _opts() {
  const o = { hour: "2-digit", minute: "2-digit", hour12: _dateFmt === "us" };
  if (_dateFmt === "iso") { o.year = "numeric"; o.month = "2-digit"; o.day = "2-digit"; }
  else { o.year = "numeric"; o.month = "short"; o.day = "numeric"; }
  if (_tz) o.timeZone = _tz;
  return o;
}

// format an ISO/UTC timestamp in the chosen zone; falls back to the raw
// string if it can't be parsed or the zone is rejected by the platform
export function formatDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  if (isNaN(d.getTime())) return iso;
  try {
    let s = new Intl.DateTimeFormat(undefined, _opts()).format(d);
    if (_dateFmt === "iso") s = s.replace(",", "");
    return s;
  } catch { return iso; }
}

// short label for the active zone (for a header/status chip)
export function tzLabel() {
  if (!_tz) return Intl.DateTimeFormat().resolvedOptions().timeZone || "local";
  return _tz.split("/").pop().replace(/_/g, " ");
}
