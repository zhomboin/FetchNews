from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="FetchNews")
    environment: str = Field(default="development")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./fetchnews.db")
    redis_url: str = Field(default="redis://localhost:6379/0")
    ingest_interval_seconds: int = Field(default=1800)
    publish_interval_seconds: int = Field(default=60)
    mock_publish_completion_seconds: int = Field(default=0)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )