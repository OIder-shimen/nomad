from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import auth, destinations, proxy, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Nomad Travel Planner API",
    description="Backend for Nomad AI travel planner — API proxy, user auth, destination management",
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

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(destinations.router, prefix="/api/destinations", tags=["Destinations"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["API Proxy"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Serve frontend static files at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")
