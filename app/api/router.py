from fastapi import APIRouter

from app.api.routes import (
    candidate_profiles,
    collectors,
    health,
    job_offers,
    matching,
)


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(candidate_profiles.router)
api_router.include_router(job_offers.router)
api_router.include_router(matching.router)
api_router.include_router(collectors.router)