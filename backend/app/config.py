from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings. Real environment variables override values from .env files.

    The repo-level `.env` (one folder above `backend/`) is read when you run
    the API from inside `backend/`; `backend/.env` can override it.
    """

    database_url: str = "postgresql+psycopg://jobtrail:jobtrail@localhost:5432/jobtrail"
    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3000"

    # --- LLM extraction (Phase 1b). "none" keeps the feature off. ---
    # "openai": the OpenAI API. "ollama": a local Ollama server (free, stays on your machine).
    llm_provider: Literal["none", "openai", "ollama"] = "none"
    llm_model: str | None = None
    # Optional override, e.g. http://host.docker.internal:11434/v1 when the API runs in Docker.
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
