from fastapi import APIRouter

from api.routes import audit, jobs, leads, outreach, proposals, scrape, settings

api_router = APIRouter(prefix="/api")

api_router.include_router(leads.router)
api_router.include_router(audit.router)
api_router.include_router(outreach.router)
api_router.include_router(proposals.router)
api_router.include_router(scrape.router)
api_router.include_router(jobs.router)
api_router.include_router(settings.router)
