// v8.15 (Roadmap Update 3 §3.4) — the live DOM-walker translator, REBUILT.
//
// The v6.6.8 architecture was sound (walk visible text nodes, batch-translate
// unique strings, swap in place, WeakMap originals for instant English
// restore, MutationObserver for newly-rendered content) — it was the backend
// protocol that failed five times, not this piece. This rebuild keeps that
// architecture with the two corrections found along the way, plus one new
// honesty feature:
//   1. NEVER String.replace(orig, tr) for the swap — `$`-sequences in the
//      replacement are treated as special patterns (a real hazard in
//      currency/price strings) and only the first occurrence swaps. The
//      node's leading/trailing whitespace is spliced back by hand instead.
//   2. [data-no-translate] subtrees are skipped — the language picker's
//      entries are endonyms ("Français", "日本語") that must always render
//      in their own script (a deliberate v6.6.9 exception, preserved).
//   3. NEW — the honesty indicator: the backend reports exactly which
//      strings could NOT be translated (roadmap §3.2's guarantee); those
//      nodes get a dotted underline + "translation unavailable" tooltip
//      instead of silently staying English with no signal.

const originals = new WeakMap();   // Text node → original English nodeValue
const nodeLang = new WeakMap();    // Text node → language it currently shows
const lastWritten = new WeakMap(); // Text node → the value WE last wrote
                                   // (distinguishes our swaps from the app's
                                   // own re-renders in the observer)
let activeLang = "en";
let observer = null;
let debounceTimer = null;

const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "CODE"]);

function skippedByAncestor(node) {
  let el = node.parentElement;
  while (el) {
    if (SKIP_TAGS.has(el.tagName)) return true;
    if (el.hasAttribute && el.hasAttribute("data-no-translate")) return true;
    el = el.parentElement;
  }
  return false;
}

// forRestore: no content heuristics — a node translated into a non-Latin
// script must still be found on the way BACK to English.
function collectNodes(root, forRestore = false) {
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      const t = n.nodeValue;
      if (!t || !t.trim()) return NodeFilter.FILTER_REJECT;
      if (!forRestore && !/[A-Za-z]{2}/.test(t)) return NodeFilter.FILTER_REJECT;
      if (skippedByAncestor(n)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  let n;
  while ((n = walker.nextNode())) out.push(n);
  return out;
}

function writeNode(node, value) {
  lastWritten.set(node, value);
  node.nodeValue = value;
}

function markMissed(el, missed) {
  if (!el) return;
  if (missed) {
    el.classList.add("i18n-missed");
    if (!el.title) el.title = "translation unavailable";
  } else if (el.classList.contains("i18n-missed")) {
    el.classList.remove("i18n-missed");
    if (el.title === "translation unavailable") el.removeAttribute("title");
  }
}

async function translateNodes(nodes, lang) {
  // group nodes by their ORIGINAL trimmed string (originals, not the current
  // nodeValue, which may already be a translation)
  const byString = new Map();
  for (const n of nodes) {
    if (nodeLang.get(n) === lang) continue;   // already showing this language
    const orig = originals.has(n) ? originals.get(n) : n.nodeValue;
    const key = orig.trim();
    if (!key || key.length < 2) continue;
    if (!byString.has(key)) byString.set(key, []);
    byString.get(key).push(n);
  }
  const texts = [...byString.keys()];
  for (let off = 0; off < texts.length && activeLang === lang; off += 200) {
    const slice = texts.slice(off, off + 200);
    let resp = null;
    try {
      const r = await fetch("/api/i18n/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang, texts: slice }),
      });
      if (r.ok) resp = await r.json();
    } catch { /* backend unreachable — nodes stay English, retried later */ }
    if (!resp || activeLang !== lang) return;
    const missedIdx = new Set(resp.untranslated || []);
    slice.forEach((src, i) => {
      const tr = resp.translations[i];
      for (const node of byString.get(src) || []) {
        if (!node.isConnected) continue;
        if (!originals.has(node)) originals.set(node, node.nodeValue);
        const orig = originals.get(node);
        const lead = (orig.match(/^\s*/) || [""])[0];
        const trail = (orig.match(/\s*$/) || [""])[0];
        // splice whitespace by hand — never String.replace (correction #1)
        writeNode(node, lead + tr + trail);
        // a missed string keeps a distinct tag so a later full pass retries
        // it instead of considering it done
        nodeLang.set(node, missedIdx.has(i) ? lang + ":missed" : lang);
        markMissed(node.parentElement, missedIdx.has(i));
      }
    });
  }
}

function startObserver(lang) {
  stopObserver();
  observer = new MutationObserver((muts) => {
    if (activeLang !== lang) return;
    for (const m of muts) {
      if (m.type === "characterData") {
        const t = m.target;
        // the APP rewrote this node (not us): its stored original is stale —
        // forget it so the new content translates fresh instead of being
        // clobbered by an old translation
        if (lastWritten.get(t) !== t.nodeValue) {
          originals.delete(t);
          nodeLang.delete(t);
        }
      }
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (activeLang === lang) {
        translateNodes(collectNodes(document.body), lang);
      }
    }, 350);
  });
  observer.observe(document.body,
                   { childList: true, subtree: true, characterData: true });
}

function stopObserver() {
  if (observer) { observer.disconnect(); observer = null; }
  clearTimeout(debounceTimer);
}

export async function translatePage(lang) {
  if (!lang || lang === "en") { restoreEnglish(); return; }
  activeLang = lang;
  startObserver(lang);
  await translateNodes(collectNodes(document.body), lang);
}

export function restoreEnglish() {
  activeLang = "en";
  stopObserver();
  for (const n of collectNodes(document.body, /* forRestore */ true)) {
    if (originals.has(n)) {
      writeNode(n, originals.get(n));   // byte-identical original back
      nodeLang.delete(n);
    }
    markMissed(n.parentElement, false);
  }
}

export function currentLanguage() { return activeLang; }
