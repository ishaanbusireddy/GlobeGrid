"""FastAPI app entrypoint (Section 13). Serves the Section 8 REST routes and
the Section 8.2 WebSocket feed."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_events, routes_map, routes_status, routes_stories
from app.config import get_settings
from app.logging_setup import setup_logging
from app.websocket.feed_socket import broadcaster_loop, router as feed_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    task = asyncio.create_task(broadcaster_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="TalkDiplomacy Live API", lifespan=lifespan)

# Single-user local app (Section 1.1/1.2) — permissive localhost CORS so the
# separately-served Vite dev frontend (Section 3.1) can reach the API.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_stories.router)
app.include_router(routes_events.router)
app.include_router(routes_map.router)
app.include_router(routes_status.router)
app.include_router(feed_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.api_port, reload=False)
