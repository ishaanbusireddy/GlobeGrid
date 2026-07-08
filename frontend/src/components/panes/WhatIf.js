// v7 §2 — the Counterfactual Engine panel: type a perturbation, get a living
// consequence tree that diverges from the real timeline. Each branch shows its
// causal mechanism, probability, historical precedent, how many REAL archive
// events support it (chain_support), and the countries it touches — click a
// country chip and the map flies there.

import { api } from "../../api/client.js";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const DOMAIN_COLORS = {
  military: "#e0564f", economic: "#e8b445", diplomatic: "#57a8e8",
  humanitarian: "#58c98b", energy: "#c77ae0", tech: "#4fd6c7",
};
const T_ORDER = { hours: 0, days: 1, weeks: 2, months: 3 };

const EXAMPLES = [
  "What if the Strait of Hormuz closes tomorrow?",
  "What if Russia and Ukraine sign a full ceasefire next month?",
  "What if China blockades Taiwan?",
  "What if the Suez Canal is blocked for a month?",
];

function branchCard(b, ctx) {
  const col = DOMAIN_COLORS[b.domain] || "#888";
  const prob = Math.round((b.probability || 0) * 100);
  const chips = (b.affected || []).map((iso) =>
    `<button class="ap-chip cfx-country" data-iso="${esc(iso)}">${esc(iso)}</button>`).join(" ");
  return `
    <div class="cfx-branch" data-id="${esc(b.id)}" style="--dcol:${col}">
      <div class="cfx-branch-head">
        <span class="chip" style="background:${col}22;border-color:${col}">${esc(b.domain)}</span>
        <span class="cp-meta">+${esc(b.t_offset)}</span>
        <span class="cfx-prob" title="model probability">
          <span class="cfx-prob-bar" style="width:${prob}%;background:${col}"></span>
          <span class="cfx-prob-num">${prob}%</span></span>
      </div>
      <h4>${esc(b.title)}</h4>
      <p class="cfx-mech">${esc(b.mechanism || "")}</p>
      ${b.precedent ? `<p class="cp-meta">precedent: ${esc(b.precedent)}</p>` : ""}
      <p class="cp-meta">
        ${b.chain_support ? `⛓ ${b.chain_support} related events in GlobeGrid's own archive` : ""}
        ${chips ? ` · affects ${chips}` : ""}</p>
      <div class="cfx-branch-actions">
        <button class="ap-chip cfx-deepen" data-id="${esc(b.id)}">↳ deepen — what follows from this?</button>
      </div>
      <div class="cfx-dyn-children" data-children-of="${esc(b.id)}"></div>
    </div>`;
}

function renderScenario(host, sc, ctx) {
  const byLevel = { roots: [], children: {} };
  for (const b of sc.branches || []) {
    if (b.parent) (byLevel.children[b.parent] ||= []).push(b);
    else byLevel.roots.push(b);
  }
  byLevel.roots.sort((a, z) => (T_ORDER[a.t_offset] ?? 9) - (T_ORDER[z.t_offset] ?? 9));
  const renderNode = (b) => branchCard(b, ctx) +
    ((byLevel.children[b.id] || []).length
      ? `<div class="cfx-children">${byLevel.children[b.id].map(renderNode).join("")}</div>` : "");
  host.innerHTML = `
    <div class="cfx-scenario">
      <div class="cfx-divergence">
        <span class="cfx-real">◉ real timeline</span>
        <span class="cfx-arrow">⤳ divergence: <b>${esc(sc.perturbation)}</b></span>
        ${sc.ai === false ? '<span class="chip">structural fallback — configure AI for the full simulation</span>'
                          : '<span class="chip">AI simulation · grounded in the fact chain</span>'}
      </div>
      <p class="knowledge-text">${esc(sc.scenario_summary || "")}</p>
      ${(sc.grounding?.analogues || []).length
        ? `<p class="cp-meta">historical analogues from the chain: ${sc.grounding.analogues.slice(0, 4).map(esc).join(" · ")}</p>` : ""}
      <div class="cfx-tree">${byLevel.roots.map(renderNode).join("")}</div>
      ${(sc.key_indicators || []).length ? `<section><h4>What would confirm which branch is unfolding</h4>
        <ul>${sc.key_indicators.map((k) => `<li>${esc(k)}</li>`).join("")}</ul></section>` : ""}
    </div>`;
  host.querySelectorAll(".cfx-country").forEach((b) =>
    b.addEventListener("click", () => ctx.openEntity("country", b.dataset.iso)));
  // v7.1 §2 — deepen a branch: generate its child consequences on click and
  // nest them under it, so the tree is explorable, not one-shot.
  host.querySelectorAll(".cfx-deepen").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const container = host.querySelector(`.cfx-dyn-children[data-children-of="${id}"]`);
      if (!container || container.dataset.loaded) { return; }
      const branch = (sc.branches || []).find((x) => x.id === id);
      btn.disabled = true; btn.textContent = "deepening…";
      try {
        const r = await api.counterfactualExpand(sc.perturbation, branch);
        if ((r.children || []).length) {
          container.innerHTML = r.children.map((c) => branchCard(c, ctx)).join("");
          container.dataset.loaded = "1";
          btn.textContent = "↳ deepened";
          // wire the new nested branches' country chips + their own deepen
          container.querySelectorAll(".cfx-country").forEach((b) =>
            b.addEventListener("click", () => ctx.openEntity("country", b.dataset.iso)));
          container.querySelectorAll(".cfx-deepen").forEach((b) => {
            // nested branches aren't in sc.branches; disable further drilling
            b.remove();
          });
        } else {
          btn.textContent = "↳ no deeper branches (needs an AI provider)";
        }
      } catch {
        btn.disabled = false; btn.textContent = "↳ deepen — retry";
      }
    }));
}

export async function renderWhatIf(el, ctx) {
  el.innerHTML = `
    <h1>🔮 What-If — Counterfactual Engine</h1>
    <p class="cp-meta">Perturb the world and watch the consequence tree diverge
      from the real timeline — every branch mechanism-scored and checked
      against GlobeGrid's own permanent fact chain.</p>
    <div class="cfx-input-row">
      <input class="cfx-input" placeholder="What if …?" maxlength="300">
      <button class="cfx-run">simulate</button>
    </div>
    <div class="cfx-examples">${EXAMPLES.map((e) =>
      `<button class="ap-chip cfx-ex">${esc(e)}</button>`).join(" ")}</div>
    <div class="cfx-recent"></div>
    <div class="cfx-host"><p class="cp-meta">Pick an example or type your own scenario.</p></div>`;
  const input = el.querySelector(".cfx-input");
  const host = el.querySelector(".cfx-host");
  const run = async (text) => {
    if (!text.trim()) return;
    input.value = text;
    host.innerHTML = `<p class="cp-meta cfx-thinking">simulating "${esc(text)}" —
      walking the causal graph forward…</p>`;
    try {
      const sc = await api.counterfactual(text);
      renderScenario(host, sc, ctx);
    } catch {
      host.innerHTML = `<p class="cp-meta">The simulation didn't return —
        check the AI provider in Settings and try again.</p>`;
    }
    loadRecent();
  };
  el.querySelector(".cfx-run").addEventListener("click", () => run(input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(input.value); });
  el.querySelectorAll(".cfx-ex").forEach((b) =>
    b.addEventListener("click", () => run(b.textContent)));
  const loadRecent = async () => {
    const r = await api.counterfactualRecent().catch(() => ({ scenarios: [] }));
    const rec = el.querySelector(".cfx-recent");
    rec.innerHTML = (r.scenarios || []).length
      ? `<p class="cp-meta">recent: ${r.scenarios.slice(0, 5).map((s) =>
          `<button class="ap-chip cfx-re">${esc(s.perturbation.slice(0, 48))}</button>`).join(" ")}</p>`
      : "";
    rec.querySelectorAll(".cfx-re").forEach((b, i) =>
      b.addEventListener("click", () => run(r.scenarios[i].perturbation)));
  };
  loadRecent();
}
