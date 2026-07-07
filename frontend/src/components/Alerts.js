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
  }

  maybeAlert(story, severity) {
    if ((severity || 0) < this.severityFloor) return;
    const toast = document.createElement("div");
    toast.className = "breaking-toast";
    toast.innerHTML = `<span class="bt-badge">⚡ breaking</span> <span class="bt-head"></span>`;
    toast.querySelector(".bt-head").textContent =
      (story.headline || "high-severity story").slice(0, 90);
    toast.addEventListener("click", () => {
      this.onOpenStory(story.id);
      toast.remove();
    });
    this.host.appendChild(toast);
    // slide-in handled by CSS; auto-dismiss with fade
    setTimeout(() => toast.classList.add("bt-out"), 9000);
    setTimeout(() => toast.remove(), 9600);
    while (this.host.children.length > 3) this.host.firstChild.remove();
  }
}
