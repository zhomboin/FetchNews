from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    mock_publish_completion_seconds: int = Field(default=0)
    publish_real_platform: str | None = Field(default=None)
    publish_callback_secret: str | None = Field(default=None)
    telegram_bot_token: str | None = Field(default=None)
    x_bearer_token: str | None = Field(default=None)
    wechat_app_id: str | None = Field(default=None)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    auth_enabled: bool = Field(default=False)
    auth_secret_key: str = Field(default="fetchnews-dev-secret")
    access_token_expire_minutes: int = Field(default=720)
    bootstrap_admin_username: str = Field(default="admin")
    bootstrap_admin_password: str = Field(default="admin-secret")
    bootstrap_admin_display_name: str = Field(default="FetchNews Admin")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )
