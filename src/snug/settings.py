from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    # 👇 This allows unknown env vars like LANGSMITH_*, TAVILY_API_KEY, etc.
    model_config = ConfigDict(extra="ignore")

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # ---- Storage ----
    sqlite_path: str = "app.db"
    use_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"

    # ---- OpenAI / LLM ----
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4o-mini"

    # ---- Vector DB ----
    milvus_host: str = "localhost"
    milvus_port: str = "19530"
    milvus_collection: str = "rental_chunks"
    milvus_enabled: bool = False


settings = Settings()
