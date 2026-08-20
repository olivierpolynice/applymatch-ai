from fastapi import APIRouter

from app.api.routes import (
    application_drafts,
    application_automation,
    auth,
    candidate_profiles,
    collectors,
    health,
    job_offers,
    matching,
    notifications,
    validation_queue,
)


api_router = APIRouter()


api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(
    candidate_profiles.router
)
api_router.include_router(job_offers.router)
api_router.include_router(matching.router)
api_router.include_router(collectors.router)
api_router.include_router(
    validation_queue.router
)
api_router.include_router(
    application_drafts.router
)
api_router.include_router(application_automation.router)
api_router.include_router(
    notifications.router
)
