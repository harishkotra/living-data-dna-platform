from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Living Data DNA Platform"
    database_url: str = "postgresql+psycopg://dna:dna@postgres:5432/dna"

    openmetadata_url: str | None = None
    openmetadata_token: str | None = None

    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    tavily_api_key: str | None = None

    brightdata_api_token: str | None = None
    brightdata_pro_mode: bool = False
    brightdata_groups: str | None = "geo,code,research"
    brightdata_tools: str | None = None
    brightdata_mcp_base_url: str = "https://mcp.brightdata.com/mcp"

    demo_seed_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
