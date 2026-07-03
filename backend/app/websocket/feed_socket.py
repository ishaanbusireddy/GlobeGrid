"""WS /ws/feed (Section 8.1, 8.2). Pushes story_created / story_updated /
instability_updated on insert, using the exact envelope from Section 8.2:

{
  "type": "story_created" | "story_updated" | "instability_updated",
  "payload": { ... },
  "timestamp": "2026-07-02T14:31:00Z"
}

No external pub/sub broker (Section 3.1) — a background task polls the
database on a short interval and broadcasts anything new/changed since the
last poll to every connected client. State (last poll time, which stories
have been seen) lives in-process, which is fine at single-user scale.
Reconnect backoff and the 15s REST-polling fallback are client
responsibilities (Section 8.2) implemented in Phase 5; this module only has
to hold up its half of the contract.
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.api.routes_stories import story_summary
from app.db.models import InstabilityScore, Story
from app.db.session import SessionLocal
from app.logging_setup import log_with_fields

logger = logging.getLogger("feed_socket")

router = APIRouter()

# Polling cadence for the broadcaster loop — an implementation detail of the
# WS transport, not a domain threshold, so it isn't in config.yaml (Section 7.2
# is reserved for pipeline/business tunables).
_POLL_INTERVAL_SECONDS = 2.0


def _envelope(msg_type: str, payload: dict) -> dict:
    return {
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class ConnectionManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        # WebSocket.send_json() uses plain json.dumps (unlike FastAPI's HTTP
        # responses, which run through jsonable_encoder automatically) — so
        # datetime/UUID/Decimal values must be encoded explicitly here.
        encoded = jsonable_encoder(message)
        dead = []
        for connection in self._connections:
            try:
                await connection.send_json(encoded)
            except Exception as exc:  # noqa: BLE001 - a broken client must not affect others
                log_with_fields(logger, logging.WARNING, "dropping dead websocket connection", error=str(exc))
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


class _PollState:
    def __init__(self):
        self.last_checked_at = datetime.now(timezone.utc)
        self.seen_story_ids: set = set()


_state = _PollState()


def _poll_once() -> list[dict]:
    """Runs in a worker thread (SQLAlchemy session here is sync)."""
    session = SessionLocal()
    try:
        events = []
        now = datetime.now(timezone.utc)

        stories = session.query(Story).filter(Story.last_updated_at >= _state.last_checked_at).all()
        for story in stories:
            msg_type = "story_created" if story.id not in _state.seen_story_ids else "story_updated"
            _state.seen_story_ids.add(story.id)
            events.append(_envelope(msg_type, story_summary(session, story)))

        scores = session.query(InstabilityScore).filter(
            InstabilityScore.computed_at >= _state.last_checked_at
        ).all()
        for score in scores:
            events.append(_envelope("instability_updated", {
                "score": float(score.score),
                "computed_at": score.computed_at.isoformat(),
                "component_breakdown": score.component_breakdown,
            }))

        _state.last_checked_at = now
        return events
    finally:
        session.close()


async def broadcaster_loop() -> None:
    while True:
        try:
            events = await asyncio.to_thread(_poll_once)
            for event in events:
                await manager.broadcast(event)
        except Exception as exc:  # noqa: BLE001 - the feed must survive a bad poll
            log_with_fields(logger, logging.ERROR, "feed broadcaster poll failed", error=str(exc))
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


@router.websocket("/ws/feed")
async def feed_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # No client->server protocol is defined (Section 8.2); just keep
            # the connection alive and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
