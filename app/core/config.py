from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Assessment Platform API", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite+aiosqlite:///./assessment.db", alias="DATABASE_URL")
    auth_mode: str = Field(default="dev", alias="AUTH_MODE")
    dev_default_user_email: str = Field(default="learner1@example.com", alias="DEV_DEFAULT_USER_EMAIL")
    upload_dir: Path = Field(default=Path("./uploads"), alias="UPLOAD_DIR")
    enable_startup_seed: bool = Field(default=True, alias="ENABLE_STARTUP_SEED")
    default_cohort: str = Field(default="2026-fde-ramp", alias="DEFAULT_COHORT")
    llm_judge_mode: str = Field(default="stub", alias="LLM_JUDGE_MODE")
    evaluation_mode: str = Field(default="stub", alias="EVALUATION_MODE")


@lru_cache
def get_settings() -> Settings:
    return Settings()
