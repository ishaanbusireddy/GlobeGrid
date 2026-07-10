"""Section 7 — configuration loading.

Loads .env (secrets/connection info) into os.environ and config.yaml
(thresholds/intervals/weights) into a nested dict. Nothing tunable is
hardcoded in application code; every module reads from here.

Zero-install constraint: config.yaml is parsed with a minimal built-in
parser (the file is a flat two-level map of scalars) so PyYAML is not
required.
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
CONFIG_YAML_PATH = BACKEND_DIR / "config.yaml"


def _parse_scalar(raw: str):
    raw = raw.strip()
    # strip inline comments ("value   # comment") — quotes in our config
    # never contain '#', so a simple split is safe here
    if " #" in raw:
        raw = raw.split(" #", 1)[0].strip()
    if raw.startswith("["):  # inline list (v3 debate.personas) — JSON-compatible
        import json
        try:
            return json.loads(raw.replace("'", '"'))
        except json.JSONDecodeError:
            pass
    if raw == "" or raw.lower() in ("null", "~"):
        return None
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw.strip("'\"")


def load_yaml(path: Path) -> dict:
    """Minimal YAML subset parser: nested maps of scalars, 2-space indent."""
    result: dict = {}
    stack = [(-1, result)]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return result


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

CONFIG = load_yaml(CONFIG_YAML_PATH)
# config.local.yaml (gitignored) overrides defaults without touching the tracked file.
_local = BACKEND_DIR / "config.local.yaml"
if _local.exists():
    for section, values in load_yaml(_local).items():
        if isinstance(values, dict):
            CONFIG.setdefault(section, {}).update(values)
        else:
            CONFIG[section] = values


def cfg(section: str, key: str):
    """Read one tunable; raises KeyError loudly rather than inventing defaults."""
    return CONFIG[section][key]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DATABASE_URL = env("DATABASE_URL", "sqlite:///backend/data/talkdiplomacy_live.db")
CLAUDE_API_KEY = env("CLAUDE_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-sonnet-5")
ALPHAVANTAGE_API_KEY = env("ALPHAVANTAGE_API_KEY")
REDDIT_CLIENT_ID = env("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = env("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = env("REDDIT_USER_AGENT", "talkdiplomacy-live/1.0 (single-user local build)")
# v3 §4 — cross-lingual embedding space: config default is the multilingual
# model so non-English facts correlate directly by meaning; .env can still
# override. Changing this triggers ensure_embedder_consistency()'s automatic
# whole-chain re-embed at next startup.
EMBEDDING_MODEL_NAME = env(
    "EMBEDDING_MODEL_NAME",
    str(CONFIG.get("embedding", {}).get("model_name", "paraphrase-multilingual-MiniLM-L12-v2")))
API_PORT = int(env("API_PORT", "8000"))

# v7 — the single source of truth for the running patch version, shown next to
# the wordmark in the header so the owner can confirm which build is live.
APP_VERSION = "8.13.7"
LOG_LEVEL = env("LOG_LEVEL", "INFO")
LOG_DIR = env("LOG_DIR", str(REPO_ROOT / "logs"))


def sqlite_path() -> Path:
    """Resolve DATABASE_URL (sqlite:///relative/or/absolute) to a file path."""
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///"):]
    elif url.startswith("sqlite:"):
        raw = url[len("sqlite:"):].lstrip("/")
    else:
        # Non-sqlite URL (e.g. the manual's original postgresql://) — this
        # build is the zero-install SQLite adaptation, so fall back to the
        # default file rather than failing to start.
        raw = "backend/data/talkdiplomacy_live.db"
    p = Path(raw)
    if not p.is_absolute():
        p = REPO_ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
