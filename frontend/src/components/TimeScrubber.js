// v2 addendum §4 — time capsule / time-scrubber (merged feature).
// One control, two presentations: drag to any past moment (time capsule)
// or press play to animate hour-by-hour (replay). Drives the as_of query
// param; the live WebSocket feed is suspended while scrubbing and
// re-enabled on return to 'now'.
export class TimeScrubber {
  constructor(host, { onAsOfChange } = {}) {
    this.onAsOfChange = onAsOfChange || (() => {});
    this.windowHours = 7 * 24;
    this.playTimer = null;
    this.el = document.createElement("div");
    this.el.id = "time-scrubber";
    this.el.innerHTML = `
      <button class="ts-play" title="replay hour by hour">▶</button>
      <input type="range" class="ts-range" min="0" max="1000" value="1000">
      <span class="ts-label">now · live</span>
      <button class="ts-now hidden">back to now</button>`;
    host.appendChild(this.el);
    this.range = this.el.querySelector(".ts-range");
    this.label = this.el.querySelector(".ts-label");
    this.nowBtn = this.el.querySelector(".ts-now");
    this.playBtn = this.el.querySelector(".ts-play");

    this.range.addEventListener("input", () => this._apply(parseInt(this.range.value, 10)));
    this.nowBtn.addEventListener("click", () => this.reset());
    this.playBtn.addEventListener("click", () => this._togglePlay());
  }

  _asOfFor(value) {
    if (value >= 1000) return null; // now
    const hoursBack = this.windowHours * (1 - value / 1000);
    return new Date(Date.now() - hoursBack * 3600e3).toISOString().slice(0, 19) + "Z";
  }

  _apply(value) {
    const asOf = this._asOfFor(value);
    if (asOf) {
      this.label.textContent = asOf.replace("T", " ").replace("Z", " UTC");
      this.nowBtn.classList.remove("hidden");
      this.el.classList.add("scrubbing");
    } else {
      this.label.textContent = "now · live";
      this.nowBtn.classList.add("hidden");
      this.el.classList.remove("scrubbing");
    }
    this.onAsOfChange(asOf);
  }

  reset() {
    this._stopPlay();
    this.range.value = "1000";
    this._apply(1000);
  }

  _togglePlay() {
    if (this.playTimer) { this._stopPlay(); return; }
    if (parseInt(this.range.value, 10) >= 1000) this.range.value = "0";
    this.playBtn.textContent = "Pause";   // just started playing
    this.playTimer = setInterval(() => {
      const step = 1000 / this.windowHours;   // one hour per tick
      const next = Math.min(1000, parseInt(this.range.value, 10) + Math.max(1, Math.round(step)));
      this.range.value = String(next);
      this._apply(next);
      if (next >= 1000) this._stopPlay();
    }, 900);
  }

  _stopPlay() {
    if (this.playTimer) clearInterval(this.playTimer);
    this.playTimer = null;
    this.playBtn.textContent = "Play";
  }
}
