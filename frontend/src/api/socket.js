// WS /ws/feed client — Section 8.2 exactly:
//  - envelope {type, payload, timestamp}
//  - reconnect with exponential backoff on drop
//  - fall back to 15-second REST polling of GET /api/stories?since=... if
//    the socket cannot be reestablished within 60 seconds.
import { api } from "./client.js";

const POLL_INTERVAL_MS = 15000;
const FALLBACK_AFTER_MS = 60000;
const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30000;

export class FeedSocket {
  constructor({ onMessage, onStateChange }) {
    this.onMessage = onMessage;
    this.onStateChange = onStateChange || (() => {});
    this.attempts = 0;
    this.downSince = null;
    this.pollTimer = null;
    this.lastSeen = new Date().toISOString();
    this.closed = false;
  }

  start() { this._connect(); }

  stop() {
    this.closed = true;
    if (this.ws) this.ws.close();
    this._stopPolling();
  }

  _connect() {
    if (this.closed) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    try {
      this.ws = new WebSocket(`${proto}://${location.host}/ws/feed`);
    } catch {
      this._scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.attempts = 0;
      this.downSince = null;
      this._stopPolling();
      this.onStateChange("live");
    };
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.timestamp) this.lastSeen = msg.timestamp;
        this.onMessage(msg);
      } catch { /* malformed frame — ignore */ }
    };
    this.ws.onclose = () => this._scheduleReconnect();
    this.ws.onerror = () => { try { this.ws.close(); } catch { /* already closed */ } };
  }

  _scheduleReconnect() {
    if (this.closed) return;
    if (this.downSince === null) this.downSince = Date.now();
    if (Date.now() - this.downSince >= FALLBACK_AFTER_MS) this._startPolling();
    const delay = Math.min(BACKOFF_BASE_MS * 2 ** this.attempts, BACKOFF_MAX_MS);
    this.attempts += 1;
    setTimeout(() => this._connect(), delay);
  }

  _startPolling() {
    if (this.pollTimer) return;
    this.onStateChange("polling");
    this.pollTimer = setInterval(async () => {
      try {
        const data = await api.stories({ since: this.lastSeen, limit: 50 });
        for (const story of (data.stories || []).reverse()) {
          this.lastSeen = story.last_updated_at > this.lastSeen
            ? story.last_updated_at : this.lastSeen;
          this.onMessage({ type: "story_updated", payload: story,
                           timestamp: story.last_updated_at });
        }
      } catch { /* API also down — keep trying */ }
    }, POLL_INTERVAL_MS);
  }

  _stopPolling() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }
}
