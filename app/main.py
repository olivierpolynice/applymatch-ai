from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.collector_scheduler import (
    start_collector_scheduler,
    stop_collector_scheduler,
)
from app.services.profile_loader import sync_profile


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://applymatch-ai.vercel.app",
)


def get_cors_origins() -> list[str]:
    origins = list(DEFAULT_CORS_ORIGINS)
    configured_origins = os.getenv("CORS_ORIGINS", "")

    for origin in configured_origins.split(","):
        normalized_origin = origin.strip().rstrip("/")

        if normalized_origin and normalized_origin not in origins:
            origins.append(normalized_origin)

    return origins


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        sync_profile(db)

    scheduler_task = start_collector_scheduler()

    try:
        yield
    finally:
        await stop_collector_scheduler(
            scheduler_task,
        )


app = FastAPI(
    title="ApplyMatch AI API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)