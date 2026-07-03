// Phase 5 data provider: the real Section 8 API + WebSocket feed, behind the
// same interface syntheticProvider exposed in Phase 4.
import {
  fetchEvents, fetchInstability, fetchSourcesStatus, fetchStories, fetchStory,
} from './client.js';
import FeedSocket from './socket.js';

let socket = null;
let connectionState = 'connecting';
const subscribers = new Set();

function fanout(message) {
  subscribers.forEach((cb) => cb(message));
}

export default {
  name: 'live',

  getStories: () => fetchStories({ limit: 200 }),
  getStory: (id) => fetchStory(id),
  getEvents: () => fetchEvents({ limit: 2000 }),
  getInstability: (range) => fetchInstability(range),
  getSourcesStatus: () => fetchSourcesStatus(),

  subscribe(callback) {
    subscribers.add(callback);
    if (!socket) {
      socket = new FeedSocket({
        onMessage: fanout,
        onStateChange: (state) => {
          connectionState = state;
          fanout({ type: 'connection', state });
        },
      });
      socket.start();
    }
    return () => subscribers.delete(callback);
  },

  connectionState: () => connectionState,
};
