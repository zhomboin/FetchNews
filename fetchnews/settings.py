from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_AUTH_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "fetchnews-dev-secret",
        "change-this-before-exposing-the-console",
    }
)
INSECURE_ADMIN_PASSWORDS: frozenset[str] = frozenset({"admin-secret", "admin"})


class Settings(BaseSettings):
    app_name: str = Field(default="FetchNews")
    environment: str = Field(default="development")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./fetchnews.db")
    database_bootstrap_mode: str = Field(default="auto")
    redis_url: str = Field(default="redis://localhost:6379/0")
    ingest_interval_seconds: int = Field(default=1800)
    publish_interval_seconds: int = Field(default=60)
    publish_rate_limit_window_seconds: int = Field(default=300)
    source_retry_attempts: int = Field(default=2)
    source_failure_alert_threshold: int = Field(default=3)
    mock_publish_completion_seconds: int = Field(default=0)
    publish_real_platform: str | None = Field(default=None)
    publish_callback_secret: str | None = Field(default=None)
    github_token: str | None = Field(default=None)
    telegram_bot_token: str | None = Field(default=None)
    telegram_chat_id: str | None = Field(default=None)
    x_bearer_token: str | None = Field(default=None)
    wechat_app_id: str | None = Field(default=None)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    auth_enabled: bool = Field(default=False)
    auth_secret_key: str = Field(default="fetchnews-dev-secret")
    access_token_expire_minutes: int = Field(default=720)
    login_rate_limit_max_failures: int = Field(default=5)
    login_rate_limit_window_seconds: int = Field(default=60)
    login_rate_limit_block_seconds: int = Field(default=300)
    bootstrap_admin_username: str = Field(default="admin")
    bootstrap_admin_password: str = Field(default="admin-secret")
    bootstrap_admin_display_name: str = Field(default="FetchNews Admin")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )


def validate_production_secrets(settings: "Settings") -> None:
    """Fail fast when production is still using documented insecure defaults."""

    if settings.environment != "production":
        return

    problems: list[str] = []
    if settings.auth_enabled and settings.auth_secret_key in INSECURE_AUTH_SECRET_KEYS:
        problems.append("APP_AUTH_SECRET_KEY must be overridden in production")
    if settings.auth_enabled and settings.bootstrap_admin_password in INSECURE_ADMIN_PASSWORDS:
        problems.append("APP_BOOTSTRAP_ADMIN_PASSWORD must be overridden in production")
    if not (settings.publish_callback_secret or "").strip():
        problems.append("APP_PUBLISH_CALLBACK_SECRET must be configured in production")

    if problems:
        raise RuntimeError("insecure production configuration detected: " + "; ".join(problems))
