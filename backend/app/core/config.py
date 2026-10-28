from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Seekr API"
    debug: bool = False
    api_prefix: str = "/api"
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8081",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/SeekrDB"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_storage_uri: str = "memory://"

    # rabbitmq
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # whisper transcription
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "auto"
    sentence_pause_threshold_secs: float = 0.7
    sentence_max_words: int = 30
    sentence_max_duration_secs: float = 20.0
    sentence_segment_hint_tolerance_secs: float = 0.05
    embedding_model: str = "BAAI/bge-m3"
    finetuned_embedding_model: str = ""
    hf_home: str = ""

    # Third-party Kaltura deployments may use an institution-specific hostname.
    kaltura_allowed_hosts: list[str] = ["kaf.keats.kcl.ac.uk"]
    kaltura_default_partner_id: str = "2368101"

    @field_validator("kaltura_allowed_hosts", mode="before")
    @classmethod
    def parse_kaltura_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip().lower() for host in v.split(",") if host.strip()]
        return v

    # qdrantDB
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "lecture_chunks"
    qdrant_vector_size: int = 1024

    # r2 storage
    storage_bucket: str = "seekr-videos"
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_region: str = "us-east-1"
    storage_public_endpoint_url: str = ""
    storage_proxy_url: str = ""
    storage_presigned_ttl_seconds: int = 3600
    storage_max_file_size_mb: int = 2048  # 2GB

    # firebase auth
    firebase_auth_enabled: bool = False
    firebase_project_id: str = ""
    firebase_service_account_json: str = ""
    firebase_client_email: str = ""
    firebase_private_key: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
