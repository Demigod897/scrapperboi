from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://scrapperboi:scrapperboi@localhost:5432/scrapperboi"
    database_url_sync: str = "postgresql://scrapperboi:scrapperboi@localhost:5432/scrapperboi"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Meilisearch
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = "scrapperboi-dev-key"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "scrapperboi-raw"
    minio_secure: bool = False

    # Google Cloud Vision (optional)
    google_application_credentials: str = ""

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    log_level: str = "INFO"

    # Scraping
    scrape_user_agent: str = (
        "Mozilla/5.0 (compatible; ScrapperBoi/1.0; "
        "+https://scrapperboi.in/bot; regulatory-research)"
    )
    scrape_default_min_delay: float = 2.0
    scrape_default_max_delay: float = 5.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
