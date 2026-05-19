import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.routes.submission import write_tier1_results
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.models import SubmissionPublic

# Initialize logging
setup_logging()
logger = get_logger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
app.add_api_route(
    "/submissions/{id}/tier1_results",
    write_tier1_results,
    methods=["POST"],
    response_model=SubmissionPublic,
    tags=["submission"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Application started - Environment: {settings.ENVIRONMENT}")
    logger.info(f"📝 CORS Origins: {settings.all_cors_origins}")
    logger.info(f"📊 API Base URL: {settings.API_V1_STR}")
    logger.info("✅ Logging system initialized")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Application shutdown")
