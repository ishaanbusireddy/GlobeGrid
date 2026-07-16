// v7 §3 — the Situation Room panel: a threaded war-room argument between four
// persistent AI analysts (fixed doctrines), all citing the SAME tracked source
// chain. Takes render as threaded messages with persona avatars; rebuttals
// nest under the take they attack; citations are clickable story chips.

import { api } from "../../api/client.js";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function msg(p, text, cites, ctx, extraClass = "") {
  const chips = (cites || []).map((id) =>
    `<button class="ap-chip sr-cite" data-id="${esc(id)}">event ↗</button>`).join(" ");
  return `
    <div class="sr-msg ${extraClass}" style="--pcol:${p.color}">
      <div class="sr-avatar" style="background:${p.color}22;border-color:${p.color}">${p.emoji}</div>
      <div class="sr-body">
        <div class="sr-who"><b style="color:${p.color}">${esc(p.name)}</b>
          <span class="cp-meta">· ${esc(p.school)}</span></div>
        <p>${esc(text)}</p>
        ${chips ? `<div class="sr-cites">${chips}</div>` : ""}
      </div>
    </div>`;
}

export async function renderSituationRoom(el, cid, ctx) {
  el.innerHTML = `<h1>Situation Room</h1>
    <p class="cp-meta sr-loading">convening the analysts — each writes a
      doctrine-true reading of the live source chain (first open can take a
      minute on a local model)…</p>
    <div class="sr-thread"></div>`;
  let d;
  try { d = await api.situationRoom(cid); }
  catch { el.querySelector(".sr-loading").textContent =
      "The Situation Room didn't answer — try again in a moment."; return; }
  const load = el.querySelector(".sr-loading");
  const thread = el.querySelector(".sr-thread");
  const personas = Object.fromEntries((d.personas || []).map((p) => [p.id, p]));
  const names = Object.fromEntries((d.personas || []).map((p) => [p.name, p]));
  if (!d.ai_available) {
    load.textContent = d.note || "AI provider needed.";
    return;
  }
  if (!(d.takes || []).length) {
    load.textContent = "No takes generated yet — the provider may be busy; "
      + "reopen in a moment or use ↻ regenerate.";
  } else {
    load.textContent = `${d.conflict} — four doctrines, one source chain`
      + (d.generated_at ? ` · generated ${d.generated_at.slice(0, 16).replace("T", " ")}` : "");
  }
  let html = "";
  const rebutsBy = {};
  for (const r of d.rebuttals || []) {
    const target = names[r.rebuts]; // rebuttal nests under the take it attacks
    (rebutsBy[target ? target.id : "_"] ||= []).push(r);
  }
  for (const t of d.takes || []) {
    const p = personas[t.persona];
    if (!p) continue;
    html += msg(p, t.take, t.cited_story_ids, ctx);
    for (const r of rebutsBy[t.persona] || []) {
      const rp = personas[r.persona];
      if (rp) html += msg(rp, r.text, [], ctx, "sr-rebuttal");
    }
  }
  html += `<div class="sr-actions">
    <button class="ap-chip sr-refresh">↻ regenerate the room</button></div>`;
  thread.innerHTML = html;
  thread.querySelectorAll(".sr-cite").forEach((b) =>
    b.addEventListener("click", () => ctx.openStory?.(b.dataset.id)));
  thread.querySelector(".sr-refresh")?.addEventListener("click", async () => {
    thread.innerHTML = `<p class="cp-meta">re-convening…</p>`;
    try { await api.situationRoom(cid, true); } catch { /* re-render below */ }
    renderSituationRoom(el, cid, ctx);
  });
}
