// WebSocket client for WS /ws/feed (Section 8.2).
//
// Contract implemented here, verbatim from the manual:
//   "Frontend reconnects with exponential backoff on drop (matches the
//    resilience policy in 7.2) and falls back to 15-second REST polling of
//    GET /api/stories?since=... if the socket cannot be reestablished
//    within 60 seconds."
//
// While polling, reconnect attempts continue in the background; the first
// successful socket reconnect stops the poller.
import { fetchStories } from './client.js';

// Mirrors the Section 7.2 resilience defaults (backoff_multiplier: 2.0);
// the cap is scaled for an interactive client rather than an ingestion job.
const BACKOFF_MULTIPLIER = 2.0;
const BACKOFF_INITIAL_MS = 1000;
const BACKOFF_MAX_MS = 30000;
const POLL_FALLBACK_AFTER_MS = 60000;
const POLL_INTERVAL_MS = 15000;

export default class FeedSocket {
  constructor({ onMessage, onStateChange }) {
    this.onMessage = onMessage;
    this.onStateChange = onStateChange ?? (() => {});
    this.backoffMs = BACKOFF_INITIAL_MS;
    this.disconnectedAt = null;
    this.lastSeen = new Date().toISOString();
    this.pollTimer = null;
    this.reconnectTimer = null;
    this.fallbackTimer = null;
    this.closed = false;
  }

  start() {
    this.closed = false;
    this._connect();
  }

  stop() {
    this.closed = true;
    clearTimeout(this.reconnectTimer);
    clearTimeout(this.fallbackTimer);
    this._stopPolling();
    this.ws?.close();
  }

  _url() {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}/ws/feed`;
  }

  _connect() {
    if (this.closed) return;
    this._setState('connecting');
    const ws = new WebSocket(this._url());
    this.ws = ws;

    ws.onopen = () => {
      this.backoffMs = BACKOFF_INITIAL_MS;
      this.disconnectedAt = null;
      clearTimeout(this.fallbackTimer);
      this._stopPolling();
      this._setState('websocket');
    };

    ws.onmessage = (raw) => {
      const message = JSON.parse(raw.data);
      if (message.timestamp) this.lastSeen = message.timestamp;
      this.onMessage(message);
    };

    ws.onclose = () => {
      if (this.closed) return;
      if (this.disconnectedAt === null) {
        this.disconnectedAt = Date.now();
        // If the socket isn't back within 60s, drop to 15s REST polling.
        this.fallbackTimer = setTimeout(() => this._startPolling(), POLL_FALLBACK_AFTER_MS);
      }
      this._setState(this.pollTimer ? 'polling' : 'reconnecting');
      this.reconnectTimer = setTimeout(() => this._connect(), this.backoffMs);
      this.backoffMs = Math.min(this.backoffMs * BACKOFF_MULTIPLIER, BACKOFF_MAX_MS);
    };

    ws.onerror = () => ws.close();
  }

  _startPolling() {
    if (this.pollTimer || this.closed) return;
    this._setState('polling');
    const poll = async () => {
      try {
        const stories = await fetchStories({ since: this.lastSeen });
        this.lastSeen = new Date().toISOString();
        for (const story of stories) {
          this.onMessage({ type: 'story_updated', payload: story, timestamp: this.lastSeen });
        }
      } catch {
        // Backend fully unreachable — keep trying on the same 15s cadence.
      }
    };
    poll();
    this.pollTimer = setInterval(poll, POLL_INTERVAL_MS);
  }

  _stopPolling() {
    clearInterval(this.pollTimer);
    this.pollTimer = null;
  }

  _setState(state) {
    this.state = state;
    this.onStateChange(state);
  }
}
