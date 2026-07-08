// v3 §9.2 generative reactive music + v4 §12 audio overhaul.
//
// v4 fixes and additions:
//   §12.1 — the confirmed one-line volume bug (master gain was 0.06, ~6%
//           of full scale) is fixed: default comes from config
//           audio.master_gain_default (0.4) and a real in-app volume
//           slider persists the user's choice.
//   §12.2/§12.3 — selectable genre presets. The instability-reactive
//           driving logic (scale pool + tempo from the score, regional
//           voices panned against the camera) is preset-agnostic; each
//           preset only swaps oscillator/scale/rhythm character.
//   Data sonification is the one preset with different plumbing: it
//   subscribes to live event_created messages (App calls onLiveEvent)
//   and renders ingestion itself as granular blips — the sound IS the
//   pipeline, not a mood layer.
const STORAGE_KEY = "tdl_sound_on";
const VOL_KEY = "tdl_sound_vol";
const PRESET_KEY = "tdl_sound_preset";

// scale pools by instability band (semitone offsets from root)
const SCALES = [
  { max: 25, name: "calm", root: 48, steps: [0, 2, 4, 7, 9, 12, 14] },        // major pent.
  { max: 50, name: "watchful", root: 47, steps: [0, 2, 3, 5, 7, 9, 10, 12] }, // dorian
  { max: 75, name: "tense", root: 45, steps: [0, 1, 4, 5, 7, 8, 10, 12] },    // phrygian dom.
  { max: 101, name: "critical", root: 44, steps: [0, 1, 3, 6, 7, 9, 12] },    // diminished-ish
];

// modal drift (§12.3): abstract interval sets per longitude band —
// deliberately abstract scale choices, not regional instrument caricature
const DRIFT_SCALES = [
  [0, 2, 3, 7, 8, 12],        // hirajoshi-like
  [0, 1, 4, 5, 7, 8, 11],     // double harmonic-ish
  [0, 2, 4, 6, 7, 9, 11],     // lydian
  [0, 2, 3, 5, 7, 9, 10],     // dorian
  [0, 3, 5, 7, 10],           // minor pentatonic
];

// v5 §17 — `reverb` (0-1 wet send) and `cutoff` (per-note low-pass Hz) added
// so each preset gets real space and filter character, not just a dry
// oscillator. ADSR shaping is applied per note in _note().
export const PRESETS = {
  // v6.1 — ambient buzz fix: the old drone sat at droneOct -24 (root 48 → MIDI
  // 24 ≈ 32.7 Hz). A ~33 Hz fundamental is below what laptop/phone speakers can
  // reproduce, so they render it as a rattly buzz/hum. Raising it to -12 (≈65 Hz)
  // keeps the warmth but leaves the sub-rumble band empty; a gentle body lowpass
  // (`cutoff`) rounds off any residual high fizz. The master DC-block stays.
  ambient_default: { label: "ambient (default)", drone: "triangle", droneOct: -12,
    melodic: "sine", tempo: 1.0, kick: false, noise: 0, reverb: 0.3, cutoff: 2600,
    softDrone: true },
  vaporwave: { label: "technofuturistic / vaporwave", drone: "sawtooth", droneOct: -24,
    melodic: "triangle", tempo: 0.55, kick: true, kickEvery: 4, noise: 0,
    chorus: true, sidechain: true, reverb: 0.42, cutoff: 1600 },
  dune: { label: "dune-inspired", drone: "sawtooth", droneOct: -24, drone2: "sawtooth",
    melodic: "sawtooth", melodicHigh: 24, tempo: 0.7, kick: false, noise: 0.008,
    sustained: true, reverb: 0.5, cutoff: 2200 },
  metal: { label: "ambient metal", drone: "square", droneOct: -24, detune: 12,
    melodic: "square", tempo: 0.8, kick: false, noise: 0.006, distort: true,
    burstHit: true, reverb: 0.3 },
  technohouse: { label: "technohouse", drone: "sawtooth", droneOct: -24,
    melodic: "square", tempo: 1.6, kick: true, kickEvery: 2, noise: 0,
    arp: true, sidechain: true, reverb: 0.22, cutoff: 2600 },
  numbers_station: { label: "numbers station", drone: "sine", droneOct: -12,
    melodic: "sine", tempo: 0.5, kick: false, noise: 0.035, shortwave: true,
    morseOnStory: true, reverb: 0.35 },
  berlin_industrial: { label: "berlin industrial", drone: "square", droneOct: -24,
    melodic: "square", tempo: 1.9, kick: true, kickEvery: 2, kickHard: true,
    noise: 0.01, distort: true, sparseMelody: true, reverb: 0.18 },
  war_room_orchestral: { label: "war-room orchestral", drone: "sawtooth", droneOct: -24,
    orchestral: true, melodic: "sawtooth", tempo: 0.6, kick: false, noise: 0.004,
    timpaniOnSeverity: true, reverb: 0.55, cutoff: 1800 },
  data_sonification: { label: "data sonification / glitch", drone: "sine", droneOct: -24,
    melodic: "square", tempo: 1.0, kick: false, noise: 0.003, sonify: true,
    sparseMelody: true, reverb: 0.15 },
  modal_drift: { label: "modal drift", drone: "triangle", droneOct: -24,
    melodic: "sine", tempo: 0.8, kick: false, noise: 0, drift: true, reverb: 0.45 },
  arctic_calm: { label: "arctic / calm", drone: "sine", droneOct: -12,
    melodic: "sine", tempo: 0.32, kick: false, noise: 0.002, glacial: true,
    reverb: 0.6, cutoff: 1400, softDrone: true },
  // v6.1 — hard_rock_metal deleted per owner request ('doesn't work, delete it').
  // v6.1 — three new EXPERIMENTAL ambient forms. All are glacial/chimey and
  // built from the same clean primitives (no distortion), so no buzz.
  crystalline_chimes: { label: "crystalline chimes", drone: "sine", droneOct: -12,
    melodic: "sine", chime: true, bell: true, tempo: 0.5, kick: false, noise: 0,
    sparseMelody: true, reverb: 0.62, cutoff: 5200, softDrone: true },
  deep_glacier: { label: "deep glacier (experimental)", drone: "triangle", droneOct: -12,
    drone2: "sine", melodic: "sine", tempo: 0.24, kick: false, noise: 0.0015,
    glacial: true, sustained: true, sweep: true, reverb: 0.7, cutoff: 1200,
    softDrone: true },
  aurora_drift: { label: "aurora drift (experimental)", drone: "triangle", droneOct: -12,
    melodic: "triangle", tempo: 0.44, kick: false, noise: 0.001, drift: true,
    chime: true, shimmer: true, reverb: 0.66, cutoff: 3400, softDrone: true },
  // v6.6.5 — two owner-requested new tracks (one calm, one aggressive), both
  // built from the SAME clean primitives at droneOct -12 (buzz-free band) so
  // neither reintroduces the sub-rumble hum.
  nocturne_calm: { label: "nocturne (calm)", drone: "sine", droneOct: -12,
    drone2: "sine", melodic: "sine", tempo: 0.36, kick: false, noise: 0.001,
    glacial: true, sustained: true, chime: true, sparseMelody: true,
    reverb: 0.64, cutoff: 1900, softDrone: true },
  storm_front: { label: "storm front (aggressive)", drone: "triangle", droneOct: -12,
    detune: 7, melodic: "triangle", tempo: 1.7, kick: true, kickEvery: 2,
    kickHard: true, noise: 0.004, powerChord: true, timpaniOnSeverity: true,
    sidechain: true, reverb: 0.24, cutoff: 2400, softDrone: true },
  // v7.4.1 — TEN new diverse tracks (owner: "add 10 more music tracks that are
  // very diverse"). All built from the existing clean primitives at droneOct
  // -12 (buzz-free band) with softDrone, so none reintroduce the sub-rumble hum.
  oceanic_deep: { label: "oceanic deep", drone: "sine", droneOct: -12, drone2: "sine",
    melodic: "sine", tempo: 0.28, kick: false, noise: 0.0018, glacial: true,
    sustained: true, sweep: true, reverb: 0.72, cutoff: 1100, softDrone: true },
  desert_mirage: { label: "desert mirage", drone: "sawtooth", droneOct: -12,
    drone2: "sawtooth", melodic: "sawtooth", melodicHigh: 12, tempo: 0.66,
    kick: false, noise: 0.006, sustained: true, drift: true, reverb: 0.5,
    cutoff: 2000, softDrone: true },
  neon_night: { label: "neon night (synthwave)", drone: "sawtooth", droneOct: -12,
    melodic: "triangle", tempo: 1.1, kick: true, kickEvery: 4, noise: 0,
    arp: true, chorus: true, sidechain: true, reverb: 0.4, cutoff: 2200,
    softDrone: true },
  monastery: { label: "monastery (choral)", drone: "sawtooth", droneOct: -12,
    orchestral: true, melodic: "sine", tempo: 0.4, kick: false, noise: 0.002,
    sustained: true, reverb: 0.75, cutoff: 1700, softDrone: true },
  signal_static: { label: "signal & static", drone: "sine", droneOct: -12,
    melodic: "sine", tempo: 0.46, kick: false, noise: 0.03, shortwave: true,
    sparseMelody: true, reverb: 0.38, cutoff: 3000, softDrone: true },
  pulse_grid: { label: "pulse grid (techno)", drone: "sawtooth", droneOct: -12,
    melodic: "square", tempo: 1.55, kick: true, kickEvery: 2, noise: 0,
    arp: true, sidechain: true, reverb: 0.2, cutoff: 2600, softDrone: true },
  stargaze: { label: "stargaze", drone: "triangle", droneOct: -12, melodic: "triangle",
    tempo: 0.4, kick: false, noise: 0.0012, drift: true, chime: true, bell: true,
    shimmer: true, reverb: 0.68, cutoff: 3600, softDrone: true },
  iron_march: { label: "iron march (martial)", drone: "sawtooth", droneOct: -12,
    orchestral: true, melodic: "sawtooth", tempo: 0.62, kick: true, kickEvery: 4,
    kickHard: true, noise: 0.003, powerChord: true, timpaniOnSeverity: true,
    reverb: 0.4, cutoff: 1900, softDrone: true },
  zen_garden: { label: "zen garden", drone: "sine", droneOct: -12, melodic: "sine",
    tempo: 0.3, kick: false, noise: 0, chime: true, bell: true, glacial: true,
    sparseMelody: true, reverb: 0.7, cutoff: 4200, softDrone: true },
  thunderhead: { label: "thunderhead (heavy)", drone: "triangle", droneOct: -12,
    detune: 9, melodic: "triangle", tempo: 1.85, kick: true, kickEvery: 2,
    kickHard: true, noise: 0.005, powerChord: true, timpaniOnSeverity: true,
    sidechain: true, reverb: 0.26, cutoff: 2500, softDrone: true },
};

const midiHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

export class SoundEngine {
  constructor(defaultOn = false, { masterGain = 0.4, preset = "ambient_default" } = {}) {
    this.ctx = null;
    this.master = null;
    this.enabled = localStorage.getItem(STORAGE_KEY) === null
      ? defaultOn : localStorage.getItem(STORAGE_KEY) === "1";
    this.volume = localStorage.getItem(VOL_KEY) !== null
      ? parseFloat(localStorage.getItem(VOL_KEY)) : masterGain;  // §12.1
    this.presetName = localStorage.getItem(PRESET_KEY) || preset;
    this.instability = 0;
    this.regions = [];
    this.cameraYaw = 0;
    this.step = 0;
    this.seqTimer = null;
    this.lastSeverity = 1;
  }

  isEnabled() { return this.enabled; }
  preset() { return PRESETS[this.presetName] || PRESETS.ambient_default; }

  // v6.1 — music from the start without the user touching the volume toggle.
  // Autoplay policy blocks a bare AudioContext until a user gesture, so: try
  // to start now (works when the tab already has an audio activation, e.g. a
  // reload), and otherwise resume on the very first pointer/key/scroll — a
  // one-shot listener that removes itself once sound is running.
  armAutoplay() {
    if (!this.enabled) return;
    const tryStart = () => {
      if (!this.enabled) return;
      this._start();
      // AudioContext may come up "suspended" until a gesture; resume() only
      // succeeds inside a user-gesture handler, hence the listeners below.
      if (this.ctx && this.ctx.state === "running") remove();
    };
    const onGesture = () => { if (this.ctx) this.ctx.resume(); tryStart(); };
    const evs = ["pointerdown", "keydown", "touchstart", "wheel"];
    const remove = () => evs.forEach((e) =>
      window.removeEventListener(e, onGesture, true));
    evs.forEach((e) => window.addEventListener(e, onGesture, { capture: true }));
    tryStart();   // optimistic immediate attempt
  }

  setPreset(name) {
    if (!PRESETS[name]) return;
    this.presetName = name;
    localStorage.setItem(PRESET_KEY, name);
    if (this.ctx) { this._teardownBed(); this._buildBed(); }
  }

  // §12.1 — proper volume control, set once, persisted
  setVolume(v) {
    this.volume = Math.max(0, Math.min(1, v));
    localStorage.setItem(VOL_KEY, String(this.volume));
    if (this.master) {
      this.master.gain.linearRampToValueAtTime(
        this._effectiveGain(), this.ctx.currentTime + 0.15);
    }
  }

  _effectiveGain() {
    // instability still breathes ±20% around the user's chosen level
    return this.volume * (0.8 + (this.instability / 100) * 0.4);
  }

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem(STORAGE_KEY, this.enabled ? "1" : "0");
    if (this.enabled) this._start(); else this._stop();
    return this.enabled;
  }

  setInstability(score) {
    this.instability = score || 0;
    if (this.master) {
      this.master.gain.linearRampToValueAtTime(
        this._effectiveGain(), this.ctx.currentTime + 1.5);
    }
    this._retempo();
  }

  setRegions(regions) { this.regions = (regions || []).slice(0, 4); }
  setCameraYaw(yaw) { this.cameraYaw = yaw; }

  _scale() {
    const base = SCALES.find((s) => this.instability < s.max) || SCALES[SCALES.length - 1];
    const p = this.preset();
    if (p.drift && this.regions.length) {   // modal drift: most active region picks the mode
      const lon = this.regions[0].lon || 0;
      const idx = Math.floor(((lon + 180) / 360) * DRIFT_SCALES.length) % DRIFT_SCALES.length;
      return { ...base, steps: DRIFT_SCALES[idx] };
    }
    return base;
  }

  _tempoMs() {
    const bpm = (60 + this.instability * 0.9) * (this.preset().tempo || 1);
    return (60000 / Math.max(20, bpm)) / 2;
  }

  _start() {
    if (this.ctx) { this.ctx.resume(); this._buildBed(); this._startSequencer(); return; }
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.master = this.ctx.createGain();
    this.master.gain.value = this._effectiveGain();   // §12.1 — was 0.06
    // Every preset beyond ambient stacks more onto this bus: unison drone
    // voices, kicks, noise beds. With nothing but a plain gain node before
    // destination, those sums transiently exceed 0dBFS and the AudioContext
    // just hard-clips — that clipping IS the "static/farting" distortion.
    // A limiter here catches it regardless of how a preset is voiced.
    this.limiter = this.ctx.createDynamicsCompressor();
    this.limiter.threshold.value = -8;
    this.limiter.knee.value = 14;
    this.limiter.ratio.value = 14;
    this.limiter.attack.value = 0.003;
    this.limiter.release.value = 0.18;
    // v6 §17 — Ambient buzz fix: a DC-blocking highpass on the whole bus.
    // Any DC offset that sneaks in (an asymmetric shaper curve, a noise
    // impulse response with nonzero mean, a sub-audible drone fundamental)
    // otherwise sits on the output as a constant offset the speaker renders
    // as a never-ending low buzz. 26 Hz is below every musical fundamental
    // used here (root -24 semitones ≈ 37 Hz) and above the DC/rumble band.
    this.dcBlock = this.ctx.createBiquadFilter();
    this.dcBlock.type = "highpass";
    this.dcBlock.frequency.value = 26;
    this.dcBlock.Q.value = 0.5;
    this.master.connect(this.dcBlock).connect(this.limiter)
      .connect(this.ctx.destination);
    // v5 §17 — ConvolverNode reverb send: everything was dry before, which
    // reads as flat/cheap regardless of preset. A synthesized impulse
    // response gives space/depth; per-preset wet amount controls how much
    // each note/drone bleeds into it.
    this.reverb = this.ctx.createConvolver();
    this.reverb.buffer = this._makeImpulse(2.6, 2.4);
    this.reverbSend = this.ctx.createGain();
    this.reverbSend.gain.value = 1.0;   // unity summing bus; per-note sends set amount
    this.reverbSend.connect(this.reverb).connect(this.dcBlock);
    this._buildBed();
    this._startSequencer();
  }

  // v5 §17 — synthesize an exponentially-decaying noise impulse response for
  // the convolution reverb (no external IR file needed, stays zero-install)
  _makeImpulse(seconds, decay) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
      }
    }
    return buf;
  }

  _buildBed() {
    if (this.bed) this._teardownBed();
    const p = this.preset();
    const t = this.ctx.currentTime;
    const bed = { nodes: [] };
    // drone(s)
    const droneOut = this.ctx.createGain();
    droneOut.gain.value = p.glacial ? 0.22 : 0.35;
    bed.droneBase = droneOut.gain.value;
    let droneDest = droneOut;
    if (p.distort) {                       // metal/industrial: soft-clip shaper
      const shaper = this.ctx.createWaveShaper();
      // v6 §17 buzz fix — SYMMETRIC odd-length curve: the old 256-point
      // curve had no exact center sample, so a silent input mapped to
      // ≈-0.01 — a constant DC offset that leaked out as the reported
      // never-stopping background buzz. 257 points puts a true zero at
      // the middle; the master DC-block below is the belt to this brace.
      const N = 257;
      const drive = p.distortDrive || 2.6;
      const curve = new Float32Array(N);
      for (let i = 0; i < N; i++) {
        const x = (2 * i) / (N - 1) - 1;
        curve[i] = Math.tanh(drive * x);
      }
      shaper.curve = curve;
      // un-oversampled waveshaping aliases hard on saw/square input — that
      // aliasing is exactly the harsh digital buzz on the distorted presets
      shaper.oversample = "4x";
      let post = shaper;
      if (p.cabinet) {   // v6 §17 — cabinet-style EQ after the distortion
        const mid = this.ctx.createBiquadFilter();
        mid.type = "peaking"; mid.frequency.value = 720;
        mid.Q.value = 0.9; mid.gain.value = 5;
        const lp = this.ctx.createBiquadFilter();
        lp.type = "lowpass"; lp.frequency.value = 4800; lp.Q.value = 0.5;
        shaper.connect(mid).connect(lp).connect(droneOut);
        post = null;
        bed.nodes.push(mid, lp);
      }
      if (post) post.connect(droneOut);
      droneDest = shaper;
      bed.nodes.push(shaper);
    }
    // voice count known up front so multi-oscillator presets (chorus,
    // detune, drone2) sum to roughly the same peak as a single drone,
    // instead of just adding amplitude on top for every extra voice
    const voiceCount = 1 + (p.detune ? 1 : 0) + (p.chorus ? 2 : 0) + (p.drone2 ? 1 : 0);
    const perVoiceGain = 0.55 / voiceCount;
    const mkDrone = (detuneCents) => {
      const osc = this.ctx.createOscillator();
      osc.type = p.drone;
      osc.frequency.value = midiHz(this._scale().root + (p.droneOct || -24));
      osc.detune.value = detuneCents;
      const g = this.ctx.createGain();
      g.gain.value = perVoiceGain;
      osc.connect(g).connect(droneDest);
      osc.start(t);
      bed.nodes.push(osc, g);
      return osc;
    };
    bed.drones = [mkDrone(0)];
    if (p.detune) bed.drones.push(mkDrone(p.detune));          // power-chord growl
    if (p.powerChord) bed.drones.push(mkDrone(700));           // v6 §17 — the fifth
    if (p.chorus) bed.drones.push(mkDrone(7), mkDrone(-6));    // vaporwave shimmer
    if (p.drone2) bed.drones.push(mkDrone(1200));              // dune high drone
    if (p.chug) {
      // v6 §17 — palm-mute chug: a square LFO gates the drone bus between
      // ~35% and 100%, giving the rhythmic djent pump without ever hitting
      // zero (a hard zero would click at the gate edges)
      const lfo = this.ctx.createOscillator();
      lfo.type = "square"; lfo.frequency.value = p.chug;
      const lfoG = this.ctx.createGain();
      lfoG.gain.value = droneOut.gain.value * 0.33;
      droneOut.gain.value *= 0.67;
      bed.droneBase = droneOut.gain.value;
      lfo.connect(lfoG).connect(droneOut.gain);
      lfo.start(t);
      bed.nodes.push(lfo, lfoG);
    }
    if (p.orchestral) {                    // string underlay: filtered saw pair
      const lp = this.ctx.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.value = 900;
      lp.connect(droneOut);
      bed.nodes.push(lp);
      for (const cents of [-8, 8]) {
        const osc = this.ctx.createOscillator();
        osc.type = "sawtooth";
        osc.frequency.value = midiHz(this._scale().root - 12);
        osc.detune.value = cents;
        const g = this.ctx.createGain(); g.gain.value = 0.18;
        osc.connect(g).connect(lp);
        osc.start(t);
        bed.nodes.push(osc, g);
      }
    }
    // v6.1 — buzz fix: sustained-drone presets route the whole drone bus
    // through a band-limiting body filter (highpass kills sub-rumble that
    // small speakers rattle on; lowpass rounds off high fizz), and an
    // optional slow filter sweep for the glacial presets. The dry master
    // path stays intact for kicks/melodic sends.
    if (p.softDrone || p.sweep) {
      const hp = this.ctx.createBiquadFilter();
      hp.type = "highpass"; hp.frequency.value = 45; hp.Q.value = 0.4;
      const lp = this.ctx.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.value = p.cutoff || 3000; lp.Q.value = 0.5;
      droneOut.connect(hp).connect(lp).connect(this.master);
      bed.nodes.push(hp, lp);
      if (p.sweep) {   // glacial slow filter sweep
        const swp = this.ctx.createOscillator();
        swp.type = "sine"; swp.frequency.value = 0.03;
        const swpG = this.ctx.createGain();
        swpG.gain.value = (p.cutoff || 3000) * 0.4;
        swp.connect(swpG).connect(lp.frequency);
        swp.start(t);
        bed.nodes.push(swp, swpG);
      }
    } else {
      droneOut.connect(this.master);
    }
    bed.nodes.push(droneOut);
    bed.droneOut = droneOut;
    // v6.1 — shimmer: a quiet octave-up sine layered over the drone, giving
    // the aurora presets their glassy top without adding sub energy
    if (p.shimmer) {
      const osc = this.ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = midiHz(this._scale().root + (p.droneOct || -12) + 24);
      const g = this.ctx.createGain(); g.gain.value = 0.06;
      osc.connect(g).connect(this.master);
      osc.start(t);
      bed.nodes.push(osc, g);
    }
    // noise bed (shortwave static / industrial hiss / arctic air)
    if (p.noise) {
      const len = this.ctx.sampleRate * 2;
      const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      const src = this.ctx.createBufferSource();
      src.buffer = buf; src.loop = true;
      const bp = this.ctx.createBiquadFilter();
      bp.type = p.shortwave ? "bandpass" : "lowpass";
      bp.frequency.value = p.shortwave ? 2400 : 400;
      bp.Q.value = p.shortwave ? 0.7 : 0.4;
      const g = this.ctx.createGain(); g.gain.value = p.noise;
      src.connect(bp).connect(g).connect(this.master);
      src.start(t);
      bed.nodes.push(src, bp, g);
      bed.noiseGain = g;
      if (p.shortwave) {   // slow static fade like band drift
        const lfo = this.ctx.createOscillator();
        const lfoG = this.ctx.createGain();
        lfo.frequency.value = 0.07; lfoG.gain.value = p.noise * 0.7;
        lfo.connect(lfoG).connect(g.gain);
        lfo.start(t);
        bed.nodes.push(lfo, lfoG);
      }
    }
    this.bed = bed;
  }

  _teardownBed() {
    if (!this.bed) return;
    const old = this.bed;
    const t = this.ctx.currentTime;
    const FADE = 0.05;
    // Killing a live oscillator/buffer source with an immediate .stop()
    // rips the waveform to silence mid-cycle — a hard click every single
    // time a preset is switched (or sound is muted/unmuted on the same
    // preset). Fading the bed's own output gains to zero first, THEN
    // stopping the nodes shortly after, turns that click into a soft
    // crossfade — this is the fix for "everything except ambient sounds
    // broken": ambient was simply the one preset nobody ever switched INTO.
    if (old.droneOut) {
      old.droneOut.gain.cancelScheduledValues(t);
      old.droneOut.gain.setValueAtTime(old.droneOut.gain.value, t);
      old.droneOut.gain.linearRampToValueAtTime(0.0001, t + FADE);
    }
    if (old.noiseGain) {
      old.noiseGain.gain.cancelScheduledValues(t);
      old.noiseGain.gain.setValueAtTime(old.noiseGain.gain.value, t);
      old.noiseGain.gain.linearRampToValueAtTime(0.0001, t + FADE);
    }
    setTimeout(() => {
      for (const n of old.nodes) {
        try { if (n.stop) n.stop(); n.disconnect(); } catch { /* already gone */ }
      }
    }, (FADE + 0.02) * 1000);
    this.bed = null;
  }

  _startSequencer() {
    if (this.seqTimer) return;
    const tick = () => {
      if (!this.enabled || !this.ctx) return;
      this._playStep();
      this.seqTimer = setTimeout(tick, this._tempoMs());
    };
    this.seqTimer = setTimeout(tick, this._tempoMs());
  }

  _retempo() {
    if (this.bed && this.bed.drones && this.ctx) {
      const p = this.preset();
      for (const d of this.bed.drones) {
        d.frequency.linearRampToValueAtTime(
          midiHz(this._scale().root + (p.droneOct || -24)), this.ctx.currentTime + 2);
      }
    }
  }

  _playStep() {
    const p = this.preset();
    const scale = this._scale();
    const t = this.ctx.currentTime;
    this.step += 1;
    // four-on-the-floor pulse, tempo-locked to instability (§12.2)
    if (p.kick && this.step % (p.kickEvery || 2) === 0) {
      this._kick(t, p.kickHard ? 0.16 : 0.09, p.sidechain);
    }
    // melodic voice
    const melodyChance = p.sparseMelody ? 0.12 : p.glacial ? 0.18 : 0.3;
    if ((this.step % 2 === 0 && !p.sparseMelody) || Math.random() < melodyChance) {
      const degree = p.arp
        ? this.step % scale.steps.length                     // arpeggiated run
        : Math.floor(Math.random() * scale.steps.length);
      const dur = p.sustained || p.glacial ? 2.2 : p.arp ? 0.18 : 0.35;
      // v5 §17 — ADSR shaped by preset: arps pluck (short decay, low sustain),
      // sustained pads swell (slow attack, high sustain); filter cutoff applied
      const env = p.arp
        ? { attack: 0.004, decay: 0.09, sustain: 0.15, release: 0.06 }
        : p.sustained || p.glacial
          ? { attack: 0.4, decay: 0.3, sustain: 0.85, release: 0.8 }
          : { attack: 0.01, decay: 0.08, sustain: 0.55, release: 0.2 };
      const fundamental = midiHz(scale.root + 12 + (p.melodicHigh || 0)
                                 + scale.steps[degree]);
      this._note(fundamental, t, dur, p.glacial ? 0.03 : 0.05, p.melodic, 0,
                 { ...env, cutoff: p.cutoff });
      // v6.1 — chime/bell timbre: layer two quiet INHARMONIC partials
      // (≈2.01× and 3.01× the fundamental) with a long soft release. Real
      // bells are inharmonic; the slight detune from exact octaves is what
      // makes it read as a chime rather than a stacked chord.
      if (p.chime) {
        const bellEnv = { attack: 0.003, decay: 0.5, sustain: 0.0,
                          release: (p.shimmer ? 2.6 : 1.8) };
        this._note(fundamental * 2.01, t, dur + 0.6, 0.028, "sine", 0.12,
                   { ...bellEnv, cutoff: (p.cutoff || 4000) });
        this._note(fundamental * 3.01, t + 0.01, dur + 0.4, 0.018, "sine", -0.1,
                   { ...bellEnv, cutoff: (p.cutoff || 4000) });
      }
    }
    // war-room timpani on high severity (§12.3)
    if (p.timpaniOnSeverity && this.lastSeverity >= 4 && this.step % 8 === 0) {
      this._timpani(t);
      this.lastSeverity = 1;
    }
    // regional voices (preset-agnostic §9.2 logic)
    this.regions.forEach((r, i) => {
      if (this.step % (3 + i * 2) !== 0) return;
      let rel = ((r.lon || 0) * Math.PI / 180 + this.cameraYaw) % (2 * Math.PI);
      const pan = Math.max(-1, Math.min(1, Math.sin(rel)));
      const degree = (i * 2 + this.step) % scale.steps.length;
      this._note(midiHz(scale.root + 24 + scale.steps[degree]), t, 0.5,
                 0.03 * Math.min(1, r.weight || 1), p.melodic === "sine" ? "triangle" : "sine",
                 pan);
    });
  }

  _kick(t, level, sidechain) {
    const osc = this.ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(120, t);
    osc.frequency.exponentialRampToValueAtTime(38, t + 0.12);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(level, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
    osc.connect(g).connect(this.master);
    osc.start(t); osc.stop(t + 0.25);
    if (sidechain && this.bed && this.bed.droneOut) {   // duck the pads
      // setTargetAtTime approaches exponentially instead of jumping — an
      // instant gain step here was clicking audibly on every single kick
      const dg = this.bed.droneOut.gain;
      const base = this.bed.droneBase || 0.35;
      dg.cancelScheduledValues(t);
      dg.setTargetAtTime(base * 0.3, t, 0.015);
      dg.setTargetAtTime(base, t + 0.06, 0.28);
    }
  }

  _timpani(t) {
    const osc = this.ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(72, t);
    osc.frequency.exponentialRampToValueAtTime(55, t + 0.4);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.14, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 1.1);
    osc.connect(g).connect(this.master);
    osc.start(t); osc.stop(t + 1.2);
  }

  _note(freq, t, dur, gainVal, type, pan, opts = {}) {
    const p = this.preset();
    const osc = this.ctx.createOscillator();
    osc.type = type;
    osc.frequency.value = freq;
    // v5 §17 — proper ADSR envelope (attack/decay/sustain/release) instead of
    // a raw on/off ramp, so percussive presets get a real pluck/hit shape
    const gain = this.ctx.createGain();
    const peak = Math.max(0.0002, gainVal);
    const A = opts.attack ?? 0.006, D = opts.decay ?? 0.05;
    const S = opts.sustain ?? 0.6, R = opts.release ?? Math.min(0.25, dur * 0.5);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.linearRampToValueAtTime(peak, t + A);              // attack
    gain.gain.linearRampToValueAtTime(peak * S, t + A + D);      // decay->sustain
    gain.gain.setValueAtTime(peak * S, t + Math.max(A + D, dur - R));
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur + R); // release
    // v5 §17 — optional per-note low-pass shaping (BiquadFilter) for the
    // 'filtered pad' character several presets call for
    let head = gain;
    if (opts.cutoff) {
      const lp = this.ctx.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.value = opts.cutoff;
      lp.Q.value = opts.resonance || 0.7;
      osc.connect(lp).connect(gain);
    } else {
      osc.connect(gain);
    }
    let node = head;
    if (this.ctx.createStereoPanner) {
      const panner = this.ctx.createStereoPanner();
      panner.pan.value = pan;
      head.connect(panner);
      node = panner;
    }
    node.connect(this.master);
    // v5 §17 — parallel reverb send (space/depth); dry stays on master
    if (this.reverbSend && (p.reverb || 0) > 0) {
      const send = this.ctx.createGain();
      send.gain.value = p.reverb;
      node.connect(send).connect(this.reverbSend);
    }
    osc.start(t);
    osc.stop(t + dur + R + 0.05);
  }

  _stop() {
    if (this.seqTimer) { clearTimeout(this.seqTimer); this.seqTimer = null; }
    if (this.ctx) this.ctx.suspend();
  }

  // story_created blip (v2 §5.2) — numbers-station preset renders it as a
  // short morse burst instead (§12.3)
  blip() {
    if (!this.enabled || !this.ctx) return;
    // v6.6.6 — rate-limit the live-feed blip. With by-the-minute ingestion a
    // burst of story_created events used to stack overlapping chimes into a
    // continuous "buzz" (owner: "the live feed sound causes infinite buzzing").
    // One blip per 700ms at most; extra arrivals in the window are silent.
    const nowMs = (this.ctx.currentTime * 1000);
    if (this._lastBlipMs && nowMs - this._lastBlipMs < 700) return;
    this._lastBlipMs = nowMs;
    const p = this.preset();
    const t = this.ctx.currentTime;
    const scale = this._scale();
    if (p.morseOnStory) {
      const pattern = [1, 0, 1, 1, 0, 1];   // dit dah-ish
      let off = 0;
      for (const bit of pattern) {
        if (bit) this._note(880, t + off, 0.07, 0.06, "sine", 0);
        off += 0.11;
      }
      return;
    }
    if (p.burstHit) {   // metal: distorted transient tied to story bursts
      this._note(midiHz(scale.root - 12), t, 0.5, 0.12, "square", 0);
      this._kick(t, 0.12, false);
      return;
    }
    // v7.4 — a crisp, obvious "ping" (owner: "make the noise that plays when
    // events stream in more obvious and pingy"). The 700ms rate-limit above
    // still prevents the old buzz, so each individual arrival can be a clear
    // bell-like notification: a bright two-tone with a fast bell attack, a
    // short ringing decay and a little more presence than the soft v6.6.2 chime.
    const ping = { attack: 0.004, decay: 0.09, sustain: 0.12, release: 0.28,
                   cutoff: 5200, resonance: 1.1 };
    // bright fundamental + an octave shimmer = a recognizable "ding-ping"
    this._note(midiHz(scale.root + 24), t, 0.32, 0.095, "sine", 0, ping);
    this._note(midiHz(scale.root + 31), t + 0.055, 0.28, 0.07, "triangle", 0, ping);
    this._note(midiHz(scale.root + 36), t + 0.11, 0.22, 0.045, "sine", 0, ping);
  }

  noteSeverity(sev) { this.lastSeverity = Math.max(this.lastSeverity, sev || 1); }

  // v6.6.4 — distinct analyst open/close cues. These play even when the music
  // engine is off (they lazily create/resume the context), because they're UI
  // feedback, not the ambient bed. Open = a bright rising shimmer (energy
  // forming); close = a soft descending settle (energy dispersing).
  _ensureCtx() {
    if (!this.ctx) {
      try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch { return null; }
      if (!this.master) { this.master = this.ctx.createGain();
        this.master.gain.value = this.volume ?? 0.4; this.master.connect(this.ctx.destination); }
    }
    if (this.ctx.state === "suspended") this.ctx.resume().catch(() => {});
    return this.ctx;
  }
  _uiTone(freq, t, dur, gain, type, opts) {
    this._note(freq, t, dur, gain, type, 0, opts);
  }
  analystOpen() {
    const ctx = this._ensureCtx(); if (!ctx) return;
    const t = ctx.currentTime;
    const chime = { attack: 0.01, decay: 0.1, sustain: 0.4, release: 0.35, cutoff: 3200, resonance: 0.7 };
    // rising perfect-fourth+octave shimmer
    this._uiTone(523, t, 0.28, 0.05, "triangle", chime);
    this._uiTone(698, t + 0.06, 0.30, 0.045, "sine", chime);
    this._uiTone(1046, t + 0.13, 0.34, 0.04, "sine", chime);
  }
  analystClose() {
    const ctx = this._ensureCtx(); if (!ctx) return;
    const t = ctx.currentTime;
    const soft = { attack: 0.008, decay: 0.14, sustain: 0.3, release: 0.4, cutoff: 1800, resonance: 0.5 };
    // descending settle
    this._uiTone(784, t, 0.26, 0.045, "sine", soft);
    this._uiTone(523, t + 0.07, 0.30, 0.04, "triangle", soft);
    this._uiTone(392, t + 0.14, 0.36, 0.038, "sine", soft);
  }

  // §12.3 data sonification: one granular blip per live event_created —
  // pitch by severity, pan by longitude, texture by category
  onLiveEvent(ev) {
    if (!this.enabled || !this.ctx || !this.preset().sonify) return;
    // v6.6.6 — throttle the sonification grains so a stream of arrivals can't
    // pile into a continuous buzz (max one grain cluster per 300ms).
    const nowMs = this.ctx.currentTime * 1000;
    if (this._lastSonifyMs && nowMs - this._lastSonifyMs < 300) return;
    this._lastSonifyMs = nowMs;
    const t = this.ctx.currentTime;
    const sev = ev.severity || 1;
    const lon = (ev.location && ev.location.lon) || 0;
    const pan = Math.max(-1, Math.min(1, lon / 180));
    const base = 1400 - sev * 180;
    for (let i = 0; i < 2 + sev; i++) {   // grain cluster
      const jitter = (Math.random() - 0.5) * 220;
      this._note(base + jitter, t + i * 0.03, 0.05, 0.05, "square", pan);
    }
  }
}
