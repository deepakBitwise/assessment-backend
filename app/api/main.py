from fastapi import APIRouter

from app.api.routes import assessment, files, items, login, private, submission, users, utils
from app.core.config import settings
from app.api.routes import human_review

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(assessment.router)
api_router.include_router(files.router)
api_router.include_router(submission.router)
api_router.include_router(human_review.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
