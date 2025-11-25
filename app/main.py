from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.redis import close_redis
from app.api import auth, persons, divisions, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title="UnserEvent API",
    description="Event management API for sports clubs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(divisions.router)
app.include_router(teams.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {"status": "ok", "message": "UnserEvent API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
