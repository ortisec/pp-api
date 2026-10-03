from fastapi import APIRouter

from app.api.v1.routers import admin, auth, results, votes, ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(votes.router)
api_router.include_router(results.router)
api_router.include_router(ws.router)

__all__ = ["api_router"]
