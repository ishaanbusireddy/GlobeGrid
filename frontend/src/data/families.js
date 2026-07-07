// v6.1.1 — language & religion FAMILY colouring for the thematic map modes.
// Genetically-related families sit near each other on the hue wheel, so a
// glance groups them (Iranian and Indo-Aryan — both Indo-Iranian — read as
// neighbouring warm reds; Slavic and Baltic as neighbouring magentas), and
// within a family each language gets a small lightness step so it's still
// tellable apart. The hover tooltip names the exact language/religion/sect,
// so no colour key is needed.

// family -> { hue (0-360), langs: [...] }. Placement favours genetic proximity.
const LANGUAGE_FAMILIES = {
  "Iranian (Indo-Iranian)": { hue: 8, langs: ["Persian", "Dari", "Tajik", "Pashto"] },
  "Indo-Aryan (Indo-Iranian)": { hue: 22, langs: ["Hindi", "Bengali", "Punjabi", "Nepali", "Sinhala", "Dhivehi"] },
  "Romance (Italic)": { hue: 38, langs: ["French", "Spanish", "Portuguese", "Italian", "Romanian", "Catalan"] },
  "French/Portuguese creole": { hue: 46, langs: ["Haitian Creole", "Mauritian Creole", "Seychellois Creole", "Crioulo", "Papiamento"] },
  "Turkic": { hue: 60, langs: ["Turkish", "Azerbaijani", "Kazakh", "Kyrgyz", "Turkmen", "Uzbek"] },
  "Mongolic": { hue: 72, langs: ["Mongolian"] },
  "Sinitic (Sino-Tibetan)": { hue: 96, langs: ["Mandarin Chinese", "Cantonese"] },
  "Tibeto-Burman (Sino-Tibetan)": { hue: 108, langs: ["Burmese", "Dzongkha"] },
  "Kra-Dai": { hue: 122, langs: ["Thai", "Lao"] },
  "Bantu (Niger-Congo)": { hue: 134, langs: ["Swahili", "Zulu", "Shona", "Kinyarwanda", "Kirundi", "Luganda", "Chichewa", "Bemba", "Setswana", "Sesotho", "Swazi", "Oshiwambo", "Comorian"] },
  "West African (Niger-Congo)": { hue: 146, langs: ["Wolof", "Fula", "Bambara", "Mandinka", "Ewe", "Sango", "Mooré", "Hausa", "Krio"] },
  "Nilo-Saharan": { hue: 152, langs: ["Dinka"] },
  "Austroasiatic": { hue: 138, langs: ["Vietnamese", "Khmer"] },
  "Austronesian": { hue: 165, langs: ["Malay", "Indonesian", "Filipino", "Malagasy", "Samoan", "Tongan", "Bislama", "Gilbertese", "Marshallese", "Nauruan", "Palauan", "Tuvaluan", "Tetum", "Tok Pisin", "Pijin"] },
  "Kartvelian": { hue: 190, langs: ["Georgian"] },
  "Armenian (Indo-European)": { hue: 200, langs: ["Armenian"] },
  "Eskimo-Aleut": { hue: 185, langs: ["Greenlandic"] },
  "Germanic (Indo-European)": { hue: 215, langs: ["English", "German", "Dutch", "Danish", "Norwegian", "Swedish", "Icelandic", "Faroese", "Luxembourgish"] },
  "Japonic": { hue: 245, langs: ["Japanese"] },
  "Koreanic": { hue: 256, langs: ["Korean"] },
  "Semitic (Afroasiatic)": { hue: 278, langs: ["Arabic", "Hebrew", "Amharic", "Tigrinya", "Maltese"] },
  "Cushitic (Afroasiatic)": { hue: 288, langs: ["Somali"] },
  "Uralic": { hue: 302, langs: ["Finnish", "Estonian", "Hungarian"] },
  "Baltic (Balto-Slavic)": { hue: 330, langs: ["Latvian", "Lithuanian"] },
  "Slavic (Balto-Slavic)": { hue: 346, langs: ["Russian", "Ukrainian", "Polish", "Czech", "Slovak", "Bulgarian", "Serbian", "Croatian", "Bosnian", "Slovene", "Macedonian", "Montenegrin"] },
  "Hellenic (Indo-European)": { hue: 168, langs: ["Greek"] },
  "Albanian (Indo-European)": { hue: 178, langs: ["Albanian"] },
};

// build language -> { hue, family, light } (small lightness step within family)
export const LANGUAGE_INFO = {};
for (const [family, { hue, langs }] of Object.entries(LANGUAGE_FAMILIES)) {
  langs.forEach((l, i) => {
    LANGUAGE_INFO[l] = { hue, family, light: 52 + (i % 5) * 6 - 6 };
  });
}

// religions: one hue per tradition (data has no sub-sect granularity yet)
export const RELIGION_INFO = {
  "Christianity": { hue: 212, family: "Christianity", light: 55 },
  "Islam": { hue: 140, family: "Islam", light: 45 },
  "Hinduism": { hue: 28, family: "Hinduism", light: 55 },
  "Buddhism": { hue: 45, family: "Buddhism", light: 55 },
  "Judaism": { hue: 258, family: "Judaism", light: 58 },
  "Unaffiliated": { hue: 0, family: "Unaffiliated", light: 60, sat: 0 },
};

// HSL -> rgba() css string
export function familyColor(info, alpha = 0.72) {
  if (!info) return `rgba(140,150,170,${alpha})`;
  const h = info.hue, s = info.sat != null ? info.sat : 62, l = info.light || 52;
  const c = (1 - Math.abs(2 * l / 100 - 1)) * (s / 100);
  const x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l / 100 - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0]; else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x]; else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c]; else [r, g, b] = [c, 0, x];
  return `rgba(${Math.round((r + m) * 255)},${Math.round((g + m) * 255)},${Math.round((b + m) * 255)},${alpha})`;
}
