// v6.1.1 — language & religion FAMILY colouring for the thematic map modes.
// Genetically-related families sit near each other on the hue wheel, so a
// glance groups them (Iranian and Indo-Aryan — both Indo-Iranian — read as
// neighbouring warm reds; Slavic and Baltic as neighbouring magentas), and
// within a family each language gets a small lightness step so it's still
// tellable apart. The hover tooltip names the exact language/religion/sect,
// so no colour key is needed.

// v8.13.4 — hues RE-SPREAD across the full wheel (owner: "why are the vietic/tai
// and austronesian and sino-tibetan-burmese groups so similarly coloured? that
// makes them seem related … fix"). Genuinely-related families still sit within
// ~12° of each other (Indo-Iranian pair, Sino-Tibetan pair, Balto-Slavic pair,
// Afroasiatic Semitic/Cushitic pair — reading as related is CORRECT there), but
// every UNRELATED neighbour is now ≥12° apart, and the four East/SE-Asian
// families that used to all read as "green" are pulled to clearly different
// bands: Kra-Dai (Tai) = yellow-green, Sino-Tibetan = green, Austroasiatic
// (Vietic) = teal, Austronesian = cyan. `sat` per family adds a second axis so
// even hue-neighbours differ in vividness. Semitic langs are ordered so Arabic
// (family-min shade) and Hebrew (family-max shade) land at opposite ends of the
// within-family gradient — Hebrew reads clearly distinct from the Arabic sea
// around it (owner: "make hebrew colour more visible compared to arabic").
const LANGUAGE_FAMILIES = {
  "Iranian (Indo-Iranian)": { hue: 4, sat: 70, langs: ["Persian", "Dari", "Tajik", "Pashto", "Balochi", "Kurdish", "Hazaragi"] },
  "Indo-Aryan (Indo-Iranian)": { hue: 18, sat: 68, langs: ["Hindi", "Bengali", "Punjabi", "Nepali", "Sinhala", "Dhivehi"] },
  "Romance (Italic)": { hue: 32, sat: 72, langs: ["French", "Spanish", "Portuguese", "Italian", "Romanian", "Catalan"] },
  "French/Portuguese creole": { hue: 44, sat: 60, langs: ["Haitian Creole", "Mauritian Creole", "Seychellois Creole", "Crioulo", "Papiamento"] },
  "Turkic": { hue: 56, sat: 74, langs: ["Turkish", "Azerbaijani", "Kazakh", "Kyrgyz", "Turkmen", "Uzbek"] },
  "Mongolic": { hue: 68, sat: 60, langs: ["Mongolian"] },
  "Kra-Dai": { hue: 82, sat: 70, langs: ["Thai", "Lao", "Shan", "Zhuang"] },
  "Sinitic (Sino-Tibetan)": { hue: 100, sat: 66, langs: ["Mandarin Chinese", "Cantonese"] },
  "Tibeto-Burman (Sino-Tibetan)": { hue: 113, sat: 58, langs: ["Burmese", "Dzongkha", "Tibetan", "Karen", "Rakhine", "Mon", "Kachin (Jingpho)", "Chin", "Karenni", "Yi", "Ladakhi", "Sikkimese", "Mizo"] },
  "Nilo-Saharan": { hue: 128, sat: 50, langs: ["Dinka"] },
  "Bantu (Niger-Congo)": { hue: 140, sat: 60, langs: ["Swahili", "Zulu", "Xhosa", "Northern Sotho", "Southern Sotho", "Shona", "Kinyarwanda", "Kirundi", "Luganda", "Chichewa", "Bemba", "Setswana", "Sesotho", "Swazi", "Oshiwambo", "Comorian"] },
  "West African (Niger-Congo)": { hue: 152, sat: 52, langs: ["Wolof", "Fula", "Bambara", "Mandinka", "Ewe", "Sango", "Mooré", "Hausa", "Krio"] },
  "Kartvelian": { hue: 164, sat: 46, langs: ["Georgian"] },
  "Austroasiatic": { hue: 177, sat: 64, langs: ["Vietnamese", "Khmer"] },
  "Austronesian": { hue: 190, sat: 66, langs: ["Malay", "Indonesian", "Filipino", "Malagasy", "Samoan", "Tongan", "Bislama", "Gilbertese", "Marshallese", "Nauruan", "Palauan", "Tuvaluan", "Tetum", "Tok Pisin", "Pijin", "Javanese", "Sundanese", "Balinese", "Acehnese", "Minangkabau", "Batak", "Minahasan"] },
  "Eskimo-Aleut": { hue: 202, sat: 40, langs: ["Greenlandic"] },
  "Armenian (Indo-European)": { hue: 214, sat: 54, langs: ["Armenian"] },
  "Germanic (Indo-European)": { hue: 226, sat: 64, langs: ["English", "German", "Dutch", "Afrikaans", "Danish", "Norwegian", "Swedish", "Icelandic", "Faroese", "Luxembourgish"] },
  "Hellenic (Indo-European)": { hue: 240, sat: 50, langs: ["Greek"] },
  "Japonic": { hue: 254, sat: 60, langs: ["Japanese"] },
  "Koreanic": { hue: 266, sat: 58, langs: ["Korean"] },
  "Semitic (Afroasiatic)": { hue: 280, sat: 62, langs: ["Arabic", "Amharic", "Tigrinya", "Harari", "Maltese", "Hebrew"] },
  "Cushitic (Afroasiatic)": { hue: 292, sat: 52, langs: ["Somali", "Oromo", "Afar"] },
  // v8.13.7 — Dravidian (South India + Sri Lanka Tamil) as its own family, and
  // the SE-Asian minority tongues now surfaced at div2 folded into their real
  // families (Austronesian for the Indonesian languages, Tibeto-Burman for the
  // Myanmar highlands, Kra-Dai for Shan, Iranian for Balochi).
  "Dravidian": { hue: 8, sat: 56, langs: ["Tamil", "Telugu", "Kannada", "Malayalam", "Tulu"] },
  "Uralic": { hue: 306, sat: 56, langs: ["Finnish", "Estonian", "Hungarian"] },
  "Albanian (Indo-European)": { hue: 320, sat: 50, langs: ["Albanian"] },
  "Baltic (Balto-Slavic)": { hue: 334, sat: 58, langs: ["Latvian", "Lithuanian"] },
  "Slavic (Balto-Slavic)": { hue: 348, sat: 66, langs: ["Russian", "Ukrainian", "Polish", "Czech", "Slovak", "Bulgarian", "Serbian", "Croatian", "Bosnian", "Slovene", "Macedonian", "Montenegrin"] },
};

// v8.13.4 — build language -> { hue, family, light, sat } as a within-family
// GRADIENT (owner: "make sure each dialect/language/religion/sect has its own
// distinct colour granularly, esp compared to those around it"). Each language
// in a family gets BOTH a small hue offset spread across the family's width AND
// a distinct lightness along a 40→72 ramp, so sibling languages are clearly
// tellable apart (not just repeating one of five lightness buckets as before).
export const LANGUAGE_INFO = {};
for (const [family, fam] of Object.entries(LANGUAGE_FAMILIES)) {
  const { hue, sat = 62, langs } = fam;
  const N = langs.length;
  langs.forEach((l, i) => {
    const t = N > 1 ? i / (N - 1) : 0.5;                 // 0..1 across the family
    const spread = Math.min(18, 6 + N * 1.4);            // total hue width
    const hueOff = (t - 0.5) * spread;                   // ±spread/2
    const light = 40 + t * 32;                           // 40..72 gradient
    LANGUAGE_INFO[l] = { hue: hue + hueOff, family, light, sat };
  });
}

// religions: one hue per tradition (data has no sub-sect granularity yet)
export const RELIGION_INFO = {
  "Christianity": { hue: 212, family: "Christianity", light: 55 },
  "Islam": { hue: 140, family: "Islam", light: 45 },
  "Hinduism": { hue: 28, family: "Hinduism", light: 55 },
  "Buddhism": { hue: 45, family: "Buddhism", light: 55 },
  "Judaism": { hue: 258, family: "Judaism", light: 58 },
  "Druze": { hue: 168, family: "Druze", light: 42, sat: 40 },   // v8.13.7
  "Shinto": { hue: 350, family: "Shinto", light: 58, sat: 55 },   // v8.16 — Japan
  "Chinese folk religion": { hue: 56, family: "Folk / syncretic", light: 56, sat: 40 },   // v8.16
  "Unaffiliated": { hue: 0, family: "Unaffiliated", light: 60, sat: 0 },
};

// v8.9 — RELIGIOUS SECT colouring. The rule (owner): sects of the SAME religion
// share a base hue, and more-similar sects sit at nearer shades. So Islam is a
// green family — Sunni a deep dark green, the Shia branches lighter yellowish
// greens (Twelver/Ismaili/Zaydi/Alawite as neighbouring shades), Ibadi a
// distinct teal-green; Christianity a blue family — Catholic deep blue,
// Protestant a lighter cyan-blue, Orthodox an indigo-blue; and so on. Explicit
// entries for the curated vocabulary + a keyword fallback so any new sect still
// lands in the right family.
export const SECT_INFO = {
  // Islam — green (base hue ~140)
  "Sunni": { hue: 142, sat: 66, light: 30, family: "Sunni Islam" },
  "Sunni (Hui)": { hue: 148, sat: 60, light: 38, family: "Sunni Islam" },
  "Twelver Shia": { hue: 104, sat: 60, light: 52, family: "Shia Islam" },
  "Twelver/Ismaili Shia": { hue: 100, sat: 58, light: 56, family: "Shia Islam" },
  "Ismaili Shia": { hue: 112, sat: 58, light: 60, family: "Shia Islam" },
  "Zaydi Shia": { hue: 94, sat: 58, light: 58, family: "Shia Islam" },
  "Alawite":      { hue: 178, sat: 50, light: 52, family: "Alawite" },   // v8.16 — own sect, own hue (not a Shia shade)
  "Ibadi": { hue: 166, sat: 60, light: 40, family: "Ibadi Islam" },
  "Ahmadiyya": { hue: 128, sat: 50, light: 68, family: "Islam (other)" },
  // Christianity — blue (base hue ~212)
  "Catholic": { hue: 214, sat: 64, light: 40, family: "Catholic" },
  "Maronite Catholic": { hue: 220, sat: 60, light: 46, family: "Catholic" },
  "Protestant": { hue: 199, sat: 62, light: 60, family: "Protestant" },
  "Protestant (Baptist)": { hue: 195, sat: 60, light: 62, family: "Protestant" },
  "Protestant (Presbyterian)": { hue: 202, sat: 60, light: 58, family: "Protestant" },
  "Protestant / Donyi-Polo": { hue: 205, sat: 52, light: 64, family: "Protestant" },
  "Anglican": { hue: 206, sat: 58, light: 54, family: "Protestant" },
  "Evangelical": { hue: 191, sat: 60, light: 66, family: "Protestant" },
  "Latter-day Saint (LDS)": { hue: 186, sat: 55, light: 60, family: "Christianity (other)" },
  "Orthodox": { hue: 228, sat: 58, light: 48, family: "Orthodox" },
  "Oriental Orthodox": { hue: 234, sat: 56, light: 44, family: "Orthodox" },
  "Coptic Orthodox": { hue: 238, sat: 56, light: 42, family: "Orthodox" },
  // Hinduism — orange (base hue ~28)
  "Hindu (Shaivite/Vaishnavite)": { hue: 28, sat: 64, light: 50, family: "Hinduism" },
  "Hindu (mixed, ~45% non-Hindu)": { hue: 34, sat: 58, light: 60, family: "Hinduism" },
  "Hindu / Catholic mix": { hue: 40, sat: 52, light: 58, family: "Hinduism" },
  "Hindu / Christian mix": { hue: 38, sat: 52, light: 62, family: "Hinduism" },
  // Buddhism — amber-gold (base hue ~45)
  "Theravada Buddhist": { hue: 45, sat: 66, light: 50, family: "Buddhism" },
  "Mahayana Buddhist": { hue: 52, sat: 62, light: 58, family: "Buddhism" },
  "Vajrayana Buddhist": { hue: 38, sat: 66, light: 46, family: "Buddhism" },
  "Shinto": { hue: 350, sat: 55, light: 58, family: "Shinto" },   // v8.16 — Japan
  // v8.13.7 — Druze (a distinct Levantine tradition), Balinese Hindu
  "Druze": { hue: 168, sat: 42, light: 42, family: "Druze" },
  "Sunni / Druze": { hue: 155, sat: 50, light: 46, family: "Druze" },
  "Balinese Hindu": { hue: 22, sat: 62, light: 52, family: "Hinduism" },
  // Judaism / Sikhism / folk / none
  "Judaism (Rabbinic)": { hue: 258, sat: 58, light: 56, family: "Judaism" },
  "Sikh (Khalsa)": { hue: 16, sat: 70, light: 44, family: "Sikhism" },
  "Chinese folk / Buddhist": { hue: 56, sat: 40, light: 56, family: "Folk / syncretic" },
  "Irreligious": { hue: 0, sat: 0, light: 60, family: "Unaffiliated" },
  // broad religion names (when a unit only has country-level religion, no sect)
  "Islam": { hue: 140, sat: 55, light: 45, family: "Islam" },
  "Christianity": { hue: 212, sat: 55, light: 55, family: "Christianity" },
  "Hinduism": { hue: 28, sat: 60, light: 55, family: "Hinduism" },
  "Buddhism": { hue: 45, sat: 60, light: 55, family: "Buddhism" },
  "Judaism": { hue: 258, sat: 55, light: 58, family: "Judaism" },
  "Sikhism": { hue: 16, sat: 65, light: 50, family: "Sikhism" },
  "Unaffiliated": { hue: 0, sat: 0, light: 60, family: "Unaffiliated" },
};

// keyword fallback so a curated value we didn't enumerate still lands in-family
export function sectInfo(v) {
  if (!v) return null;
  if (SECT_INFO[v]) return SECT_INFO[v];
  const s = v.toLowerCase();
  if (s.includes("ibadi")) return SECT_INFO["Ibadi"];
  if (s.includes("shia") || s.includes("shi'a")) return SECT_INFO["Twelver Shia"];
  if (s.includes("sunni") || s.includes("islam")) return SECT_INFO["Sunni"];
  if (s.includes("orthodox")) return SECT_INFO["Orthodox"];
  if (s.includes("catholic")) return SECT_INFO["Catholic"];
  if (s.includes("protestant") || s.includes("evangel") || s.includes("anglic")
      || s.includes("baptist")) return SECT_INFO["Protestant"];
  if (s.includes("christian")) return SECT_INFO["Christianity"];
  if (s.includes("buddh")) return SECT_INFO["Theravada Buddhist"];
  if (s.includes("hindu")) return SECT_INFO["Hindu (Shaivite/Vaishnavite)"];
  if (s.includes("sikh")) return SECT_INFO["Sikh (Khalsa)"];
  if (s.includes("jud") || s.includes("jewish")) return SECT_INFO["Judaism"];
  return { hue: 220, sat: 12, light: 60, family: "other" };
}

// v8.9 — DIALECT colouring: a dialect inherits its parent LANGUAGE's family hue
// (so all Arabic dialects are warm Semitic tones, all English dialects Germanic
// blues…), with a deterministic per-dialect lightness step so sibling dialects
// read as near-but-distinct shades. Keyword-matched to the language family.
const _DIALECT_LANG_KEYWORDS = [
  ["arabic", "Arabic"], ["english", "English"], ["spanish", "Spanish"],
  ["french", "French"], ["portuguese", "Portuguese"], ["german", "German"],
  ["persian", "Persian"], ["farsi", "Persian"], ["dari", "Dari"],
  ["mandarin", "Mandarin Chinese"], ["putonghua", "Mandarin Chinese"],
  ["cantonese", "Cantonese"], ["yue", "Cantonese"], ["hindi", "Hindi"],
  ["bengali", "Bengali"], ["punjabi", "Punjabi"], ["tamil", "Tamil"],
  ["telugu", "Telugu"], ["kurdish", "Kurdish"], ["dutch", "Dutch"],
  ["flemish", "Dutch"], ["italian", "Italian"], ["russian", "Russian"],
  ["urdu", "Urdu"], ["swahili", "Swahili"], ["malay", "Malay"],
  ["catalan", "Catalan"], ["basque", "Basque"], ["galician", "Galician"],
];
function _strHash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
export function dialectInfo(v, langInfoLookup) {
  if (!v) return null;
  const s = v.toLowerCase();
  let base = null;
  for (const [kw, lang] of _DIALECT_LANG_KEYWORDS) {
    if (s.includes(kw)) { base = langInfoLookup ? langInfoLookup(lang) : LANGUAGE_INFO[lang]; break; }
  }
  // direct language name (no dialect qualifier) → its own language info
  if (!base) base = (langInfoLookup ? langInfoLookup(v) : LANGUAGE_INFO[v]) || null;
  // v8.13.4 — the dialect map now carries the SAME "related-languages gradient"
  // as the language/sect modes (owner: "make sure the dialect map has that
  // related-languages gradient colour scheme … each dialect its own distinct
  // colour granularly"). A dialect inherits its parent language's family hue,
  // then a deterministic per-dialect hue offset (±7°) AND a 7-step lightness
  // ramp (36→72) pick a clearly-distinct sibling shade — so e.g. the Arabic
  // dialects fan out as near-but-separable Semitic tones instead of collapsing
  // onto ~5 repeated shades.
  const baseHue = base ? base.hue : (_strHash(s) % 360);
  const hueOff = ((_strHash(s + "#h") % 15) - 7);        // ±7°
  const light = 36 + (_strHash(s) % 7) * 6;              // 36,42,…,72
  const hue = ((baseHue + hueOff) % 360 + 360) % 360;
  const family = base ? base.family : "other";
  return { hue, sat: base ? (base.sat || 62) : 45, light, family };
}

// HSL -> rgba() css string
// v8.13 — climate map-mode colours: one intuitive hue per Köppen main group,
// each its own legend "family" so the grouped legend names them.
const CLIMATE_INFO = {
  "Tropical":    { hue: 140, sat: 58, light: 40, family: "Tropical" },
  "Arid":        { hue: 38,  sat: 72, light: 55, family: "Arid" },
  "Temperate":   { hue: 82,  sat: 52, light: 48, family: "Temperate" },
  "Continental": { hue: 210, sat: 55, light: 52, family: "Continental" },
  "Polar":       { hue: 195, sat: 30, light: 74, family: "Polar" },
  "Highland":    { hue: 280, sat: 34, light: 56, family: "Highland" },
};
export function climateInfo(v) { return CLIMATE_INFO[v] || null; }

// v8.13.6 — government / regime type map-mode colours: a spectrum from open
// (green democracy) through monarchy blues to closed (red authoritarian / one-
// party) plus purple theocracy and grey military-transitional.
const GOV_INFO = {
  "Democracy":               { hue: 140, sat: 60, light: 45, family: "Democracy" },
  "Partial democracy":       { hue: 95,  sat: 58, light: 50, family: "Partial democracy" },
  "Constitutional monarchy": { hue: 205, sat: 58, light: 52, family: "Constitutional monarchy" },
  "Absolute monarchy":       { hue: 268, sat: 46, light: 46, family: "Absolute monarchy" },
  "Authoritarian":           { hue: 8,   sat: 66, light: 46, family: "Authoritarian" },
  "One-party state":         { hue: 350, sat: 60, light: 34, family: "One-party state" },
  "Theocracy":               { hue: 300, sat: 40, light: 40, family: "Theocracy" },
  "Military / transitional": { hue: 32,  sat: 30, light: 45, family: "Military / transitional" },
};
export function govInfo(v) { return GOV_INFO[v] || { hue: 220, sat: 10, light: 55, family: "other" }; }

// v8.16 — ruling-party ideology (the Ideology map mode). The left→right
// political spectrum reads as the classic red→blue sweep (far-left deep red,
// social democracy rose, centrism yellow-grey, liberalism sky, conservatism
// deep blue, right-populism navy-violet), with non-party regimes in the same
// off-spectrum colors as the government map (junta grey-brown, monarchy
// purple, theocracy magenta-purple, personalist dark red-brown).
const IDEOLOGY_INFO = {
  "Communism (one-party)":      { hue: 355, sat: 72, light: 32, family: "Left" },
  "Socialism":                  { hue: 0,   sat: 66, light: 44, family: "Left" },
  "Left-wing populism":         { hue: 12,  sat: 62, light: 50, family: "Left" },
  "Social democracy":           { hue: 340, sat: 52, light: 55, family: "Left" },
  "Green politics":             { hue: 120, sat: 55, light: 42, family: "Left" },
  "Centrism":                   { hue: 48,  sat: 30, light: 55, family: "Center" },
  "Liberalism":                 { hue: 200, sat: 58, light: 55, family: "Center" },
  "Christian democracy":        { hue: 215, sat: 42, light: 48, family: "Right" },
  "Conservatism":               { hue: 225, sat: 58, light: 42, family: "Right" },
  "Nationalism":                { hue: 250, sat: 50, light: 42, family: "Right" },
  "Right-wing populism":        { hue: 262, sat: 58, light: 38, family: "Right" },
  "Islamism":                   { hue: 155, sat: 48, light: 36, family: "Religious" },
  "Theocracy":                  { hue: 300, sat: 40, light: 40, family: "Religious" },
  "Absolute monarchy":          { hue: 268, sat: 46, light: 46, family: "Non-party" },
  "Military rule":              { hue: 32,  sat: 30, light: 45, family: "Non-party" },
  "Personalist authoritarian":  { hue: 8,   sat: 60, light: 30, family: "Non-party" },
};
export function ideologyInfo(v) {
  return IDEOLOGY_INFO[v] || { hue: 220, sat: 10, light: 55, family: "other" };
}

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
