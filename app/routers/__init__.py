from fastapi import APIRouter

from .oauth import router as oauth2_router
from .auth import router as auth_router
from .referrers import router as referrers_router

api_router = APIRouter()

api_router.include_router(oauth2_router, tags=["OAuth2"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(referrers_router, tags=["Referrer"])
