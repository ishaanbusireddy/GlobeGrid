// Active data source for the app. Phase 4: the Section 12 synthetic dataset.
// Phase 5 swaps this export for the live API provider (src/api/) — rendering
// code imports only this module and never knows the difference.
import syntheticProvider from './syntheticProvider.js';

export default syntheticProvider;
