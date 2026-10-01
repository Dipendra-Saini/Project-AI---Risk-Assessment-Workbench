from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{REPO_ROOT / 'raw.db'}"
    checkpoint_url: str = ""  # "memory" | sqlite path | postgres url; derived if empty
    jwt_secret: str = "dev-only-secret"
    jwt_ttl_minutes: int = 12 * 60

    llm_mode: str = "live"  # live | offline | replay
    llm_record: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    llm_timeout_s: float = 30.0
    embed_dim: int = 768

    token_budget_per_case: int = 12000
    otel_exporter_otlp_endpoint: str = ""
    pipeline_sync: bool = False

    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def prompts_dir(self) -> Path:
        return REPO_ROOT / "ai" / "prompts"

    @property
    def config_dir(self) -> Path:
        return REPO_ROOT / "config"

    @property
    def recordings_path(self) -> Path:
        return REPO_ROOT / "evals" / "recordings" / "llm_recordings.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
