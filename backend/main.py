from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import init_db
from routers import auth, destinations, proxy, admin

# In-memory session tracker for real online count
_online_sessions: dict[str, float] = {}
_ONLINE_TTL = 90  # seconds before a session is considered offline


class PingRequest(BaseModel):
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TD Travel Planner API",
    description="Backend for TD AI travel planner — API proxy, user auth, destination management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/online/ping")
async def online_ping(body: PingRequest):
    """Heartbeat ping from active users. Returns current online count."""
    now = time.time()
    _online_sessions[body.session_id] = now
    # Clean expired sessions
    expired = [sid for sid, ts in _online_sessions.items() if now - ts > _ONLINE_TTL]
    for sid in expired:
        del _online_sessions[sid]
    return {"online": len(_online_sessions)}


@app.get("/api/online/count")
async def online_count():
    """Get current online count without registering a ping."""
    now = time.time()
    expired = [sid for sid, ts in _online_sessions.items() if now - ts > _ONLINE_TTL]
    for sid in expired:
        del _online_sessions[sid]
    return {"online": len(_online_sessions)}


app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(destinations.router, prefix="/api/destinations", tags=["Destinations"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["API Proxy"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Serve frontend static files at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")
