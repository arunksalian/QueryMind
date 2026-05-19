from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    # PostgreSQL
    postgres_dsn: str = Field(
        "postgresql://querymind:changeme@localhost:5432/querymind_dev",
        alias="POSTGRES_DSN",
    )

    # MongoDB
    mongo_uri: str = Field("mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field("querymind_dev", alias="MONGO_DB")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    session_ttl_seconds: int = Field(86400, alias="SESSION_TTL_SECONDS")

    # Qdrant
    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field("querymind_memory", alias="QDRANT_COLLECTION")

    # n8n
    n8n_base_url: str = Field("http://localhost:5678", alias="N8N_BASE_URL")
    n8n_api_key: str = Field("", alias="N8N_API_KEY")

    # API
    query_default_limit: int = Field(100, alias="QUERY_DEFAULT_LIMIT")


settings = Settings()
