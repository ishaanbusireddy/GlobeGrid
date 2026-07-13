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
// v8.15.1 — strings currently out for translation: overlapping passes must
// never fire a second request for text that's already awaiting a reply.
const pendingStrings = new Set();
let activeLang = "en";
let observer = null;
let debounceTimer = null;
let followUpTimer = null;          // progressive-fill pass for `deferred`

// v8.15.1 — one HTTP call now maps to ~1-2 real model batches (server-side
// batches are 20 strings), instead of the old 200-string chunk that chained
// 10 sequential generations inside a single request.
const CHUNK = 40;

function scheduleFollowUp(lang, opts) {
  if (followUpTimer || activeLang !== lang) return;
  // the follow-up keeps the caller's interactive priority but NEVER retries
  // known-failed strings — those are only re-attempted by an explicit user
  // switch, so a persistent model failure can't be re-hammered every pass
  const next = { interactive: !!(opts && opts.interactive), retryMissed: false };
  followUpTimer = setTimeout(() => {
    followUpTimer = null;
    if (activeLang === lang) {
      translateNodes(collectNodes(document.body), lang, next);
    }
  }, 1500);
}

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

async function translateNodes(nodes, lang, opts = {}) {
  const interactive = !!opts.interactive;
  const retryMissed = !!opts.retryMissed;
  // group nodes by their ORIGINAL trimmed string (originals, not the current
  // nodeValue, which may already be a translation)
  const byString = new Map();
  for (const n of nodes) {
    const tag = nodeLang.get(n);
    if (tag === lang) continue;               // already showing this language
    // a string the model genuinely FAILED on is only retried by an explicit
    // user switch, never in a background loop (that would hammer the model
    // with a known-bad string on every feed tick)
    if (!retryMissed && tag === lang + ":missed") continue;
    const orig = originals.has(n) ? originals.get(n) : n.nodeValue;
    const key = orig.trim();
    if (!key || key.length < 2) continue;
    if (pendingStrings.has(key)) continue;    // already out for translation
    if (!byString.has(key)) byString.set(key, []);
    byString.get(key).push(n);
  }
  const texts = [...byString.keys()];
  let anyDeferred = false;
  for (let off = 0; off < texts.length && activeLang === lang; off += CHUNK) {
    const slice = texts.slice(off, off + CHUNK);
    slice.forEach((s) => pendingStrings.add(s));
    let resp = null;
    try {
      const r = await fetch("/api/i18n/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang, texts: slice, interactive }),
      });
      if (r.ok) resp = await r.json();
    } catch { /* backend unreachable — retried by the follow-up pass */
    } finally {
      slice.forEach((s) => pendingStrings.delete(s));
    }
    if (!resp) { scheduleFollowUp(lang, opts); return; }
    if (activeLang !== lang) return;
    const missedIdx = new Set(resp.untranslated || []);
    const deferredIdx = new Set(resp.deferred || []);
    if (deferredIdx.size) anyDeferred = true;
    slice.forEach((src, i) => {
      // deferred = not attempted this call (gate busy / budget spent):
      // leave the node completely untouched — the follow-up pass retries it
      if (deferredIdx.has(i)) return;
      const tr = resp.translations[i];
      for (const node of byString.get(src) || []) {
        if (!node.isConnected) continue;
        if (!originals.has(node)) originals.set(node, node.nodeValue);
        const orig = originals.get(node);
        const lead = (orig.match(/^\s*/) || [""])[0];
        const trail = (orig.match(/\s*$/) || [""])[0];
        // splice whitespace by hand — never String.replace (correction #1)
        writeNode(node, lead + tr + trail);
        nodeLang.set(node, missedIdx.has(i) ? lang + ":missed" : lang);
        markMissed(node.parentElement, missedIdx.has(i));
      }
    });
  }
  // progressive fill: while anything came back deferred, keep one (and only
  // one) queued follow-up pass alive until the page is fully translated
  if (anyDeferred) scheduleFollowUp(lang, opts);
}

function startObserver(lang) {
  stopObserver();
  observer = new MutationObserver((muts) => {
    if (activeLang !== lang) return;
    // v8.15.1 — only mutations we actually care about schedule a rescan:
    // added nodes, or text the APP rewrote (not our own swaps, which would
    // otherwise self-trigger a wasted full-page walk after every batch).
    let relevant = false;
    for (const m of muts) {
      if (m.type === "characterData") {
        const t = m.target;
        if (lastWritten.get(t) !== t.nodeValue) {
          // the app rewrote this node: its stored original is stale — forget
          // it so the new content translates fresh instead of being
          // clobbered by an old translation
          originals.delete(t);
          nodeLang.delete(t);
          relevant = true;
        }
      } else if (m.type === "childList" && m.addedNodes && m.addedNodes.length) {
        relevant = true;
      }
    }
    if (!relevant) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (activeLang === lang) {
        // background pass: yields instantly server-side if translation is
        // already running; never re-hammers known-failed strings
        translateNodes(collectNodes(document.body), lang,
                       { interactive: false, retryMissed: false });
      }
    }, 350);
  });
  observer.observe(document.body,
                   { childList: true, subtree: true, characterData: true });
}

function stopObserver() {
  if (observer) { observer.disconnect(); observer = null; }
  clearTimeout(debounceTimer);
  clearTimeout(followUpTimer);
  followUpTimer = null;
}

export async function translatePage(lang) {
  if (!lang || lang === "en") { restoreEnglish(); return; }
  activeLang = lang;
  startObserver(lang);
  // the user's own explicit switch: interactive (waits its turn at the
  // gate) and retries even previously-failed strings once
  await translateNodes(collectNodes(document.body), lang,
                       { interactive: true, retryMissed: true });
}

export function restoreEnglish() {
  activeLang = "en";
  stopObserver();
  pendingStrings.clear();
  for (const n of collectNodes(document.body, /* forRestore */ true)) {
    if (originals.has(n)) {
      writeNode(n, originals.get(n));   // byte-identical original back
      nodeLang.delete(n);
    }
    markMissed(n.parentElement, false);
  }
}

export function currentLanguage() { return activeLang; }
