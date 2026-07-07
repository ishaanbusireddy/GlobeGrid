"""v2 addendum §3.5 — per-article sentiment/tone, -1..1.

Zero-install-consistent lexicon scorer (small built-in valence lexicon +
negation flip + intensity modifiers). Auto-upgrades to a proper model if
one is installed later — same detect pattern as embeddings/NER: if VADER
(nltk or vaderSentiment) is importable it is used instead.
"""

import logging
import re

log = logging.getLogger("sentiment")

_POSITIVE = {
    "agreement": 2, "aid": 1, "breakthrough": 3, "calm": 2, "ceasefire": 2,
    "celebrate": 2, "cooperation": 2, "cure": 2, "eases": 2, "gain": 1, "gains": 1,
    "growth": 2, "help": 1, "hope": 2, "improve": 2, "improved": 2, "peace": 3,
    "progress": 2, "rally": 1, "rebound": 2, "recovery": 2, "relief": 2, "rescue": 2,
    "resolution": 2, "restore": 1, "reunite": 2, "rise": 1, "stability": 2,
    "success": 2, "support": 1, "surge": 1, "thrive": 2, "treaty": 2, "truce": 2,
    "victory": 2, "welcome": 1, "wins": 1,
}
_NEGATIVE = {
    "attack": -3, "bomb": -3, "bombing": -3, "casualties": -3, "catastrophe": -3,
    "chaos": -2, "clash": -2, "collapse": -3, "conflict": -2, "crackdown": -2,
    "crash": -2, "crisis": -2, "dead": -3, "deadly": -3, "death": -3, "deaths": -3,
    "default": -2, "destroy": -3, "destroyed": -3, "disaster": -3, "displaced": -2,
    "erupt": -1, "escalate": -2, "evacuate": -2, "explosion": -3, "famine": -3,
    "fear": -2, "fears": -2, "fire": -1, "flee": -2, "flood": -2, "invasion": -3,
    "kill": -3, "killed": -3, "kills": -3, "loss": -1, "losses": -2, "massacre": -3,
    "missile": -2, "outbreak": -2, "panic": -2, "plunge": -2, "protest": -1,
    "recession": -2, "refugee": -1, "riot": -2, "sanction": -1, "sanctions": -1,
    "shelling": -3, "shortage": -2, "slump": -2, "strike": -1, "tension": -1,
    "tensions": -1, "terror": -3, "threat": -2, "threats": -2, "turmoil": -2,
    "unrest": -2, "victim": -2, "victims": -2, "violence": -3, "war": -3,
    "warning": -1, "worst": -2, "wounded": -3,
}
_NEGATORS = frozenset("not no never without denies denied halts stops prevented".split())
_INTENSIFIERS = {"very": 1.4, "extremely": 1.7, "major": 1.3, "massive": 1.5,
                 "severe": 1.5, "slight": 0.6, "minor": 0.6, "limited": 0.7}
_TOKEN_RE = re.compile(r"[a-z']+")

_model = None
_tried = False


def _vader():
    global _model, _tried
    if not _tried:
        _tried = True
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
            _model = SentimentIntensityAnalyzer()
            log.info("sentiment_backend", extra={"data": {"backend": "vader"}})
        except Exception:  # noqa: BLE001
            try:
                from nltk.sentiment import SentimentIntensityAnalyzer  # type: ignore
                _model = SentimentIntensityAnalyzer()
                log.info("sentiment_backend", extra={"data": {"backend": "nltk-vader"}})
            except Exception:  # noqa: BLE001
                _model = None
                log.info("sentiment_backend",
                         extra={"data": {"backend": "lexicon (stdlib fallback)"}})
    return _model


def score_text(text: str) -> float:
    """Sentiment in [-1, 1]; 0 is neutral."""
    model = _vader()
    if model is not None:
        try:
            return float(model.polarity_scores(text[:2000])["compound"])
        except Exception:  # noqa: BLE001
            pass
    tokens = _TOKEN_RE.findall((text or "").lower())
    total, hits = 0.0, 0
    for i, tok in enumerate(tokens):
        valence = _POSITIVE.get(tok) or _NEGATIVE.get(tok)
        if valence is None:
            continue
        weight = 1.0
        window = tokens[max(0, i - 2):i]
        for prev in window:
            if prev in _NEGATORS:
                valence = -valence * 0.8
            weight *= _INTENSIFIERS.get(prev, 1.0)
        total += valence * weight
        hits += 1
    if hits == 0:
        return 0.0
    return max(-1.0, min(1.0, total / (hits * 3.0)))
