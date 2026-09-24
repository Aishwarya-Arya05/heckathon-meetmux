"""
Application settings loaded from environment variables.

All configuration is read from the environment (or a .env file in development).
Secrets must NEVER be hardcoded or committed to version control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — every setting maps to an environment variable."""

    # ── Application ──────────────────────────────────────────────
    app_env: str = Field("development", description="development | staging | production")
    app_debug: bool = False
    app_log_level: str = "info"
    app_secret_key: str = Field("change-me-to-a-random-secret", description="Used for signing tokens / sessions")

    # ── Backend server ───────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 1

    # ── Neo4j ────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change-me"
    neo4j_database: str = "neo4j"

    # ── Routing provider ─────────────────────────────────────────
    routing_provider: str = Field("demo", description="'osrm' or 'demo'")
    osrm_base_url: str = "http://localhost:5000"
    osrm_timeout_seconds: int = 10

    # ── Map tiles ────────────────────────────────────────────────
    map_tile_provider: str = Field("osm", description="'osm', 'mapbox', or 'custom'")
    mapbox_access_token: Optional[str] = None
    map_tile_url: Optional[str] = None
    map_tile_attribution: Optional[str] = None

    # ── Delay prediction model ───────────────────────────────────
    model_artifact_path: Optional[str] = Field(None, description="Path to trained .joblib model")
    model_version: Optional[str] = None

    # ── CORS ─────────────────────────────────────────────────────
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Rate limiting ────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}

    # ── Derived helpers ──────────────────────────────────────────

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_demo_mode(self) -> bool:
        return self.routing_provider == "demo" and self.model_artifact_path is None

    @property
    def model_path(self) -> Optional[Path]:
        if self.model_artifact_path:
            return Path(self.model_artifact_path)
        return None


def get_settings() -> Settings:
    """Factory cached at module level — reimport-safe for testing."""
    return Settings()
