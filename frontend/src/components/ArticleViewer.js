// v8.18 — the embedded article browser (owner: "clicking a real article link
// should open it in an on-screen window, not a new browser tab").
//
// Honest constraint: most major news sites send X-Frame-Options / CSP
// frame-ancestors headers that make the browser REFUSE to render them in an
// iframe, and that refusal is invisible to JS. So the pane asks the backend
// (/api/embedcheck) which inspects the article's response headers:
//   embeddable=true  → render the article in an in-app iframe
//   embeddable=false → a clean card: "this site blocks embedding — open ↗"
//   embeddable=null  → unknown (offline/HEAD refused) — try the iframe with the
//                      open-in-tab link kept prominent alongside.
// The "Open in Tab" button is ALWAYS present, so nothing is ever lost.
import { api } from "../api/client.js";

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let host = null;

function ensureHost() {
  if (host && document.body.contains(host)) return host;
  host = document.createElement("div");
  host.id = "article-viewer";
  host.className = "hidden";
  host.innerHTML = `
    <div class="av-panel" role="dialog" aria-label="Article viewer">
      <div class="av-header">
        <span class="av-title"></span>
        <a class="av-open ap-chip" target="_blank" rel="noopener">Open in Tab ↗</a>
        <button class="av-close" title="Close (Esc)" aria-label="Close">×</button>
      </div>
      <div class="av-body"></div>
    </div>`;
  host.querySelector(".av-close").addEventListener("click", closeArticle);
  host.addEventListener("click", (e) => { if (e.target === host) closeArticle(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !host.classList.contains("hidden")) {
      e.stopPropagation(); closeArticle();
    }
  }, true);
  document.body.appendChild(host);
  return host;
}

export function closeArticle() {
  if (!host) return;
  host.classList.add("hidden");
  const body = host.querySelector(".av-body");
  if (body) body.innerHTML = "";   // drop the iframe so audio/network stops
}

export async function openArticle(url, title) {
  if (!url) return;
  const h = ensureHost();
  h.classList.remove("hidden");
  h.querySelector(".av-title").textContent = title || url.replace(/^https?:\/\//, "").slice(0, 80);
  const open = h.querySelector(".av-open");
  open.href = url;
  const body = h.querySelector(".av-body");
  body.innerHTML = `<p class="cp-meta av-status">Checking whether this site allows embedding…</p>`;
  let check = null;
  try { check = await api.embedCheck(url); } catch { check = null; }
  const embeddable = check ? check.embeddable : null;
  if (embeddable === false) {
    body.innerHTML = `
      <div class="av-blocked">
        <p><b>${esc(new URL(url).hostname)}</b> blocks being embedded inside other
           apps (a standard news-site security header), so the article can't be
           shown in this window.</p>
        <a class="ap-chip av-blocked-open" href="${esc(url)}" target="_blank" rel="noopener">Open the Article in a New Tab ↗</a>
      </div>`;
    return;
  }
  // allowed or unknown → try the iframe (the Open in Tab button stays in the
  // header either way; a blank frame on an unknown-status site means it blocked
  // us after all — the note below says so honestly).
  body.innerHTML = `
    ${embeddable === null ? `<p class="cp-meta av-status">Embedding status unknown — trying anyway. If the frame stays blank, the site blocks embedding; use Open in Tab ↗.</p>` : ""}
    <iframe class="av-frame" src="${esc(url)}" referrerpolicy="no-referrer"
      sandbox="allow-scripts allow-same-origin allow-popups"></iframe>`;
}
