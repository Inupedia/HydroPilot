from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_demo_fixture_path() -> Path:
    """Resolve the committed demo fixture in source checkouts without assuming path depth.

    Packaged desktop builds provide HYDROPILOT_DEMO_FIXTURE_PATH explicitly, so this
    default only needs to remain safe when modules are imported from PyInstaller.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "demo" / "sacramento_v0_1.json"
        if candidate.exists():
            return candidate
    return Path("data") / "demo" / "sacramento_v0_1.json"


class Settings(BaseSettings):
    """Runtime configuration for the HydroPilot API."""

    service_name: str = "hydropilot-api"
    database_url: str = "postgresql+psycopg://hydropilot:hydropilot@localhost:5432/hydropilot"
    demo_fixture_path: Path = Field(default_factory=default_demo_fixture_path)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="HYDROPILOT_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
