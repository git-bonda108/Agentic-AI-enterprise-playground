from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = API_DIR.parent.parent

# Provider keys may live in the repo root .env, apps/api/.env, or the shell environment.
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(API_DIR / ".env", override=False)


class Settings(BaseSettings):
    """Runtime configuration, read from environment or .env."""

    model_config = SettingsConfigDict(env_prefix="PLAYGROUND_", env_file=".env", extra="ignore")

    app_name: str = "Enterprise AI Playground"
    environment: str = "local"
    database_url: str = f"sqlite:///{API_DIR / 'playground.db'}"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100", "http://localhost:3101"]
    # Shared secret between the web app's route handlers and this API.
    internal_key: str = "local-internal-key"
    # Deterministic fake provider for tests and offline demos.
    fake_llm: bool = False
    # Organization allowances shown on the console until budgets land in Batch 2.
    org_credits_usd: float = 2500.0
    org_monthly_cap_usd: float = 5000.0
    default_user_cap_usd: float = 25.0
    # LangGraph checkpoint database; empty means apps/api/checkpoints.db
    checkpoint_path: str = ""
    # Azure Container Apps dynamic sessions pool endpoint; empty means the local development sandbox.
    sandbox_endpoint: str = ""
    # Where the sandbox reaches this API from (notebooks call back into the playground).
    self_url: str = "http://localhost:8000"
    # Extra local directories the repository mapper may read, comma separated. The repo root is always allowed.
    repo_roots: str = ""
    # Background canary scheduler (one tick per minute). Tests drive ticks explicitly instead.
    canary_scheduler: bool = True


settings = Settings()
