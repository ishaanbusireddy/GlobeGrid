"""Loads .env (secrets/connection info) and config.yaml (tunables) per Section 7.

Nothing tunable is hardcoded elsewhere in application code — every threshold,
interval, or weight referenced by later stages is read through this module.
"""
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BACKEND_DIR / "config.yaml"


@dataclass(frozen=True)
class Settings:
    # --- .env (Section 7.1) ---
    database_url: str
    claude_api_key: Optional[str]
    claude_model: str
    alphavantage_api_key: Optional[str]
    reddit_client_id: Optional[str]
    reddit_client_secret: Optional[str]
    reddit_user_agent: str
    embedding_model_name: str
    api_port: int
    ws_port: int
    log_level: str
    log_dir: str

    # --- config.yaml (Section 7.2) ---
    config: dict = field(default_factory=dict)

    def correlation(self) -> dict:
        return self.config["correlation"]

    def instability(self) -> dict:
        return self.config["instability"]

    def ingestion_intervals_seconds(self) -> dict:
        return self.config["ingestion_intervals_seconds"]

    def map(self) -> dict:
        return self.config["map"]

    def resilience(self) -> dict:
        return self.config["resilience"]


def _load_env() -> None:
    # Load repo-root-relative .env if present; real deployments export env vars directly.
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


def _load_config_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _env(name: str, default: Any = None, required: bool = False) -> Any:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Required environment variable {name} is not set (see backend/.env.example)")
    return value


@lru_cache(maxsize=1)
def get_settings(config_path: Optional[str] = None) -> Settings:
    _load_env()
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config = _load_config_yaml(path)

    return Settings(
        database_url=_env("DATABASE_URL", required=True),
        claude_api_key=_env("CLAUDE_API_KEY"),
        claude_model=_env("CLAUDE_MODEL", "claude-sonnet-5"),
        alphavantage_api_key=_env("ALPHAVANTAGE_API_KEY"),
        reddit_client_id=_env("REDDIT_CLIENT_ID"),
        reddit_client_secret=_env("REDDIT_CLIENT_SECRET"),
        reddit_user_agent=_env("REDDIT_USER_AGENT", "talkdiplomacy-live/1.0 (single-user local build)"),
        embedding_model_name=_env("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        api_port=int(_env("API_PORT", 8000)),
        ws_port=int(_env("WS_PORT", 8000)),
        log_level=_env("LOG_LEVEL", "INFO"),
        log_dir=_env("LOG_DIR", "./logs"),
        config=config,
    )
