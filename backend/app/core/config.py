"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationInfo, field_validator, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "extra": "ignore"
    }
    """Application settings."""

    # Application
    APP_NAME: str = "repo-auditor"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/repo_auditor"

    # CORS (comma-separated string, parsed to list)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3333"

    # Security
    API_KEY_REQUIRED: bool = True  # Enable API key auth by default
    API_KEYS: str = ""  # Comma-separated list of valid API keys
    SECRET_KEY: str = ""  # For JWT/session signing

    @field_validator("API_KEYS")
    @classmethod
    def validate_api_keys(cls, value: str, info: ValidationInfo) -> str:
        """Ensure API keys are provided when required."""
        required = info.data.get("API_KEY_REQUIRED", False)
        keys = [k.strip() for k in value.split(",") if k.strip()] if value else []

        if required and not keys:
            raise ValueError(
                "API_KEY_REQUIRED is true but API_KEYS is empty. "
                "Set API_KEYS or disable API_KEY_REQUIRED."
            )

        return value

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @computed_field
    @property
    def api_keys_list(self) -> List[str]:
        """Get API keys as list."""
        if not self.API_KEYS:
            return []
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # Git / Analysis
    CLONE_DIR: Path = Path("/tmp/repo-auditor-clones")
    CLONE_TIMEOUT: int = 120  # seconds
    MAX_REPO_SIZE_MB: int = 500

    # File Storage
    UPLOAD_DIR: Path = Path("/tmp/repo-auditor-uploads")
    S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"

    # GitHub (PAT for private repos, App for webhooks)
    GITHUB_PAT: Optional[str] = None  # Personal Access Token for cloning private repos
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_CREATE_ISSUES: bool = False

    # Semgrep
    SEMGREP_ENABLED: bool = True
    SEMGREP_RULES_DIR: Path = Path("infra/semgrep/rules")

    # Cost estimation
    REGION_MODE: str = "EU_UA"  # EU, UA, or EU_UA

    # LLM Providers
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Google Drive (for file/folder access)
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None  # Path to service account JSON file
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = None  # Root folder ID to browse

    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None  # Slack Incoming Webhook URL
    SLACK_CHANNEL: str = "#repo-auditor"  # Default channel
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    EMAIL_RECIPIENTS: str = ""  # Comma-separated email addresses
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # UI URL for notification links
    UI_URL: str = "https://ui-three-rho.vercel.app"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
