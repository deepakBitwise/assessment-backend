from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.appeals import router as appeals_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.attempts import router as attempts_router
from app.api.routes.health import router as health_router
from app.api.routes.me import router as me_router
from app.api.routes.path import router as path_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.submissions import router as submissions_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(me_router)
api_router.include_router(path_router)
api_router.include_router(assessments_router)
api_router.include_router(attempts_router)
api_router.include_router(submissions_router)
api_router.include_router(reviews_router)
api_router.include_router(appeals_router)
api_router.include_router(admin_router)
