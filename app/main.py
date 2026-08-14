from contextlib import asynccontextmanager

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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)