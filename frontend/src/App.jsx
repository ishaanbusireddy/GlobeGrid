// App root: live feed + tiered map + story pages (Section 2.1 Stage 7).
// Tier is auto-detected per Section 11.2; a manual override control is
// always visible regardless of the detected tier.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import provider from './data/dataProvider.js';
import Tier1Globe from './components/map/Tier1Globe.jsx';
import Tier2Map from './components/map/Tier2Map.jsx';
import Tier3List from './components/map/Tier3List.jsx';
import { detectTier, getTierOverride, setTierOverride } from './components/map/TierDetector.js';
import LiveFeed from './components/feed/LiveFeed.jsx';
import StoryPage from './components/story/StoryPage.jsx';

export default function App() {
  const detectedTier = useMemo(() => detectTier(), []);
  const [override, setOverride] = useState(getTierOverride());
  const tier = override ?? detectedTier;

  const [stories, setStories] = useState([]);
  const [events, setEvents] = useState([]);
  const [activeStory, setActiveStory] = useState(null);
  const [connState, setConnState] = useState(provider.connectionState());

  useEffect(() => {
    provider.getStories().then(setStories);
    provider.getEvents().then(setEvents);
    const unsubscribe = provider.subscribe((message) => {
      if (message.type === 'story_created' || message.type === 'story_updated') {
        setStories((prev) => {
          const rest = prev.filter((s) => s.id !== message.payload.id);
          return [message.payload, ...rest];
        });
        provider.getEvents().then(setEvents);
      }
      if (message.type === 'connection') setConnState(message.state);
    });
    return unsubscribe;
  }, []);

  const openStory = useCallback((id) => {
    provider.getStory(id).then(setActiveStory);
  }, []);

  const changeOverride = (value) => {
    const parsed = value === 'auto' ? null : Number(value);
    setTierOverride(parsed);
    setOverride(parsed);
  };

  return (
    <>
      <div className="topbar">
        <h1>TALKDIPLOMACY <span>LIVE</span></h1>
        <span className={`conn ${connState === 'websocket' ? 'live' : ''}`}>
          data: {connState}
        </span>
        <div className="spacer" />
        <label className="tier-override">
          Graphics tier
          <select value={override ?? 'auto'} onChange={(e) => changeOverride(e.target.value)}>
            <option value="auto">Auto (Tier {detectedTier})</option>
            <option value="1">Tier 1 — Full 3D</option>
            <option value="2">Tier 2 — 2D map</option>
            <option value="3">Tier 3 — Light</option>
          </select>
        </label>
      </div>

      <div className="layout">
        {activeStory ? (
          <StoryPage story={activeStory} onBack={() => setActiveStory(null)} />
        ) : (
          <>
            <div className="map-pane">
              {tier === 1 && (
                <Tier1Globe events={events} stories={stories} onSelectStory={openStory} />
              )}
              {tier === 2 && (
                <Tier2Map events={events} stories={stories} onSelectStory={openStory} />
              )}
              {tier === 3 && (
                <Tier3List events={events} onSelectStory={openStory} stories={stories} />
              )}
            </div>
            <div className="feed-pane">
              <LiveFeed stories={stories} onSelectStory={openStory} />
            </div>
          </>
        )}
      </div>
    </>
  );
}
