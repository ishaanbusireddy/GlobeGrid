// v4 §25 — in-app breaking-story alerts: a brief animated toast when a
// high-severity story forms while attention is elsewhere in the UI.
// Stays entirely on-screen (the 'get it off the screen' category was
// excluded by design in v3); uses the shared §18 motion variables; a
// click is a shortcut into the existing sliding pane, not a separate
// notification surface.
export class Alerts {
  constructor(hostEl, { severityFloor = 4, onOpenStory } = {}) {
    this.host = hostEl;
    this.severityFloor = severityFloor;
    this.onOpenStory = onOpenStory || (() => {});
    // v6.6.2 — user-toggleable in Settings; alerts render in their own host
    // (outside the feed panel) so they always pop even when the feed is closed
    this.enabled = localStorage.getItem("tdl_alerts_enabled") !== "0";
  }

  // v8.13.3 — returns true when a toast was actually shown, so the caller can
  // fire the matching bright "breaking" audio cue only for real alerts. The
  // toast now carries a shrinking countdown bar (`bt-timer`) and its entrance /
  // glow / shimmer are handled in CSS for a fluid, moderately-flashy pop.
  maybeAlert(story, severity) {
    if (!this.enabled) return false;
    if ((severity || 0) < this.severityFloor) return false;
    const toast = document.createElement("div");
    toast.className = "breaking-toast";
    toast.innerHTML =
      `<span class="bt-badge">⚡ breaking</span> <span class="bt-head"></span>` +
      `<span class="bt-timer"></span>`;
    toast.querySelector(".bt-head").textContent =
      (story.headline || "high-severity story").slice(0, 90);
    toast.addEventListener("click", () => {
      this.onOpenStory(story.id);
      toast.remove();
    });
    this.host.appendChild(toast);
    // slide-in / glow / shimmer handled by CSS; auto-dismiss with a fluid fade
    setTimeout(() => toast.classList.add("bt-out"), 9000);
    setTimeout(() => toast.remove(), 9600);
    while (this.host.children.length > 3) this.host.firstChild.remove();
    return true;
  }
}
