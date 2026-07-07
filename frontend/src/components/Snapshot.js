// v4 §23 — shareable snapshot export: one click, no server round-trip.
// Captures the current Tier 1 render at 1080x1080, composites the top
// story headlines, instability score, timestamp, and the §22-required
// attribution footer.
export async function exportSnapshot({ mapHost, stories, instability }) {
  const src = mapHost.querySelector("canvas");
  if (!src) throw new Error("no live render to capture");
  const SIZE = 1080;
  const out = document.createElement("canvas");
  out.width = SIZE; out.height = SIZE;
  const ctx = out.getContext("2d");

  // background + centered square crop of the live render
  ctx.fillStyle = "#0a0e17";
  ctx.fillRect(0, 0, SIZE, SIZE);
  const side = Math.min(src.width, src.height);
  ctx.drawImage(src, (src.width - side) / 2, (src.height - side) / 2, side, side,
                0, 0, SIZE, SIZE);
  // overlay canvas (cluster counts / city labels) if present
  const overlay = mapHost.querySelector(".globe-overlay");
  if (overlay && overlay.width) {
    ctx.drawImage(overlay, (overlay.width - side) / 2, (overlay.height - side) / 2,
                  side, side, 0, 0, SIZE, SIZE);
  }

  // text panel
  const grad = ctx.createLinearGradient(0, SIZE * 0.62, 0, SIZE);
  grad.addColorStop(0, "rgba(10,14,23,0)");
  grad.addColorStop(0.35, "rgba(10,14,23,0.82)");
  grad.addColorStop(1, "rgba(10,14,23,0.96)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, SIZE * 0.62, SIZE, SIZE * 0.38);

  ctx.fillStyle = "#4da3ff";
  ctx.font = "bold 34px system-ui";
  ctx.fillText("◉ GLOBEGRID", 48, SIZE - 300);
  if (instability != null) {
    ctx.fillStyle = "#ffd166";
    ctx.font = "bold 30px system-ui";
    ctx.textAlign = "right";
    ctx.fillText(`instability ${Math.round(instability)}/100`, SIZE - 48, SIZE - 300);
    ctx.textAlign = "left";
  }
  ctx.fillStyle = "#dbe4f5";
  ctx.font = "26px system-ui";
  let y = SIZE - 244;
  for (const s of (stories || []).slice(0, 3)) {
    let head = "• " + (s.headline || "");
    if (head.length > 74) head = head.slice(0, 72) + "…";
    ctx.fillText(head, 48, y);
    y += 44;
  }
  ctx.fillStyle = "#8494b5";
  ctx.font = "20px system-ui";
  ctx.fillText(new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC", 48, SIZE - 88);
  ctx.font = "16px system-ui";
  ctx.fillText("Geocoding © GeoNames (CC BY 4.0) · Boundaries: Natural Earth (public domain)",
               48, SIZE - 52);
  ctx.fillText("Every story links its sources — globegrid", 48, SIZE - 28);

  const a = document.createElement("a");
  a.href = out.toDataURL("image/png");
  a.download = `globegrid-snapshot-${new Date().toISOString().slice(0, 10)}.png`;
  a.click();
}
