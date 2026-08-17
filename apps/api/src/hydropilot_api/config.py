from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the HydroPilot API."""

    service_name: str = "hydropilot-api"
    database_url: str = "postgresql+psycopg://hydropilot:hydropilot@localhost:5432/hydropilot"
    demo_fixture_path: Path = Path(__file__).resolve().parents[4] / "data" / "demo" / "sacramento_v0_1.json"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="HYDROPILOT_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
