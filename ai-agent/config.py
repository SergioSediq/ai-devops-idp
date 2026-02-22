"""Centralized configuration for the AI DevOps Assistant."""

from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- API & LLM ---
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 4096

    # --- Vector DB ---
    chroma_persist_dir: str = "./chroma_db"
    runbook_dir: str = "./runbooks"

    # --- Kubernetes ---
    k8s_log_tail_lines: int = 200
    k8s_event_limit: int = 50
    k8s_in_cluster: bool = False  # Set True when deployed in EKS

    # --- Server ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "*"  # Comma-separated origins; restrict in prod
    log_level: str = "INFO"

    # --- Rate Limiting ---
    rate_limit_requests: int = 60  # requests per window
    rate_limit_window: int = 60  # seconds

    # --- Feature Flags ---
    enable_web_search: bool = False  # Enable when SerpAPI key is available
    serpapi_key: Optional[str] = None


settings = Settings()
