from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models import Base
from app.services.seed import seed_initial_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.enable_startup_seed:
        async with SessionLocal() as session:
            await seed_initial_data(session)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
