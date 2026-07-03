// Active data source for the app. Phase 5: the live Section 8 API +
// WebSocket feed. The Phase 4 synthetic provider remains available in
// ./syntheticProvider.js for offline frontend dev (swap the export below);
// its dataset file is purged from the DB side by scripts/purge_synthetic.py.
import liveProvider from '../api/liveProvider.js';

export default liveProvider;
