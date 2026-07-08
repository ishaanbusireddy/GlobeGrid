// v6.6.8 — site-wide live DOM translator (clean-slate rebuild).
//
// The UI is authored in English. When the user picks a language, we walk EVERY
// visible text node in the document, send the unique strings to the backend
// (/api/i18n/translate) for that language, and swap the text in place. Original
// English is preserved per node, so switching back to English restores it
// instantly. A MutationObserver translates newly-rendered text (feed updates,
// opened panels, map labels in the DOM) so the whole site stays translated.
//
// This replaces the old summary-only translation entirely.

import { api } from "./api/client.js";

const ORIG = new WeakMap();          // text node -> original English string
let currentLang = "en";
let observer = null;

// never translate inside these (code, canvas, the map GL canvas, etc.)
// v6.6.9 — OPTION text IS translated (dropdown labels like the timezone/
// language pickers): every <select> in this codebase is read by `.value`,
// never by its visible option label, so rewriting the label text is safe and
// closes the one real gap found in the v6.6.8 translation sweep.
const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "CANVAS", "CODE",
  "PRE", "TEXTAREA", "INPUT", "SELECT"]);

function acceptNode(n) {
  const t = n.nodeValue;
  if (!t || !t.trim()) return false;
  if (!/[A-Za-z]/.test(t)) return false;      // pure numbers/symbols/emoji — skip
  const p = n.parentElement;
  if (!p) return false;
  if (SKIP_TAGS.has(p.tagName)) return false;
  if (p.closest("[data-no-translate]")) return false;
  return true;
}

function collectTextNodes(root) {
  const nodes = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => acceptNode(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
  });
  let n;
  while ((n = walker.nextNode())) nodes.push(n);
  return nodes;
}

async function translateNodes(nodes, lang) {
  const targets = [];
  for (const n of nodes) {
    if (!ORIG.has(n)) ORIG.set(n, n.nodeValue);   // remember the English source
    if (lang === "en") { n.nodeValue = ORIG.get(n); continue; }   // restore
    targets.push(n);
  }
  if (lang === "en" || !targets.length) return;

  // unique trimmed strings → one server round-trip per batch, cached server-side
  const uniq = [...new Set(targets.map((n) => ORIG.get(n).trim()))];
  const map = {};
  for (let i = 0; i < uniq.length; i += 80) {
    const batch = uniq.slice(i, i + 80);
    try {
      const r = await api.i18nTranslate(lang, batch);
      Object.assign(map, r.translations || {});
    } catch { /* leave this batch in English */ }
    if (lang !== currentLang) return;   // user switched again mid-flight — abort
  }
  for (const n of targets) {
    const orig = ORIG.get(n);
    const key = orig.trim();
    const tr = map[key];
    // preserve the node's leading/trailing whitespace around the swapped text
    if (tr && tr !== key) n.nodeValue = orig.replace(key, tr);
  }
}

// Public: switch the whole site to `lang` (or restore English).
export function setLanguage(lang) {
  currentLang = lang || "en";
  translateNodes(collectTextNodes(document.body), currentLang);
}

export function currentLanguage() { return currentLang; }

// Translate content rendered after a language switch (feed items, opened panes,
// DOM map labels). Only active when a non-English language is selected.
export function startObserver() {
  if (observer) return;
  observer = new MutationObserver((muts) => {
    if (currentLang === "en") return;
    const fresh = [];
    for (const m of muts) {
      for (const node of m.addedNodes) {
        if (node.nodeType === Node.TEXT_NODE) {
          if (acceptNode(node)) fresh.push(node);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          fresh.push(...collectTextNodes(node));
        }
      }
    }
    if (fresh.length) translateNodes(fresh, currentLang);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}
