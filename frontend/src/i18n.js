// v5 §2 — expanded language support. Original text/language is always
// preserved (v1 §5.8); only UI chrome and story summaries translate on
// display via the existing /api/translate path. Simplified and Traditional
// Chinese are distinct locales (not interchangeable). RTL languages get
// real RTL layout via a body[dir=rtl] toggle, not just translated strings
// dropped into an LTR layout.
export const LANGUAGES = [
  { code: "en", name: "English", rtl: false },
  // European: every EU official language + neighbours
  { code: "bg", name: "Български", rtl: false },
  { code: "hr", name: "Hrvatski", rtl: false },
  { code: "cs", name: "Čeština", rtl: false },
  { code: "da", name: "Dansk", rtl: false },
  { code: "nl", name: "Nederlands", rtl: false },
  { code: "et", name: "Eesti", rtl: false },
  { code: "fi", name: "Suomi", rtl: false },
  { code: "fr", name: "Français", rtl: false },
  { code: "de", name: "Deutsch", rtl: false },
  { code: "el", name: "Ελληνικά", rtl: false },
  { code: "hu", name: "Magyar", rtl: false },
  { code: "ga", name: "Gaeilge", rtl: false },
  { code: "it", name: "Italiano", rtl: false },
  { code: "lv", name: "Latviešu", rtl: false },
  { code: "lt", name: "Lietuvių", rtl: false },
  { code: "mt", name: "Malti", rtl: false },
  { code: "pl", name: "Polski", rtl: false },
  { code: "pt", name: "Português", rtl: false },
  { code: "ro", name: "Română", rtl: false },
  { code: "sk", name: "Slovenčina", rtl: false },
  { code: "sl", name: "Slovenščina", rtl: false },
  { code: "es", name: "Español", rtl: false },
  { code: "sv", name: "Svenska", rtl: false },
  { code: "no", name: "Norsk", rtl: false },
  { code: "is", name: "Íslenska", rtl: false },
  { code: "uk", name: "Українська", rtl: false },
  { code: "be", name: "Беларуская", rtl: false },
  { code: "sr", name: "Српски", rtl: false },
  { code: "bs", name: "Bosanski", rtl: false },
  { code: "sq", name: "Shqip", rtl: false },
  { code: "mk", name: "Македонски", rtl: false },
  // West/Central Asia and Caucasus
  { code: "fa", name: "فارسی", rtl: true },
  { code: "tr", name: "Türkçe", rtl: false },
  { code: "ka", name: "ქართული", rtl: false },
  { code: "hy", name: "Հայերեն", rtl: false },
  { code: "az", name: "Azərbaycan", rtl: false },
  { code: "ur", name: "اردو", rtl: true },
  // ASEAN
  { code: "id", name: "Indonesia", rtl: false },
  { code: "th", name: "ไทย", rtl: false },
  { code: "vi", name: "Tiếng Việt", rtl: false },
  { code: "fil", name: "Filipino", rtl: false },
  { code: "ms", name: "Melayu", rtl: false },
  { code: "my", name: "မြန်မာ", rtl: false },
  { code: "km", name: "ខ្មែរ", rtl: false },
  { code: "lo", name: "ລາວ", rtl: false },
  // East Asia — Simplified and Traditional Chinese as distinct locales
  { code: "ja", name: "日本語", rtl: false },
  { code: "ko", name: "한국어", rtl: false },
  { code: "zh-Hans", name: "中文（简体）", rtl: false },
  { code: "zh-Hant", name: "中文（繁體）", rtl: false },
  // Other
  { code: "sw", name: "Kiswahili", rtl: false },
  { code: "he", name: "עברית", rtl: true },
  { code: "am", name: "አማርኛ", rtl: false },
  { code: "ar", name: "العربية", rtl: true },
];

// map a locale code to the human target-language name /api/translate expects
export function targetLangName(code) {
  const l = LANGUAGES.find((x) => x.code === code);
  if (!l) return "English";
  // disambiguate the two Chinese locales for the translator
  if (code === "zh-Hans") return "Simplified Chinese";
  if (code === "zh-Hant") return "Traditional Chinese";
  return l.name.replace(/\s*\(.*\)/, "");
}

export function isRTL(code) {
  const l = LANGUAGES.find((x) => x.code === code);
  return !!(l && l.rtl);
}

// apply the chosen UI language: set the document dir for real RTL layout
// (the panel system flips) and persist the choice
export function applyLanguage(code) {
  localStorage.setItem("tdl_lang", code);
  document.documentElement.setAttribute("lang", code);
  document.documentElement.setAttribute("dir", isRTL(code) ? "rtl" : "ltr");
}
