from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "ollama"
    ollama_model: str = "ollama/llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    demo_mode: bool = True
    fail_on_missing_api: bool = False
    max_budget_optimization_rounds: int = 2
    contingency_percent: float = 10.0

    tavily_api_key: str | None = None
    openweather_api_key: str | None = None
    google_maps_api_key: str | None = None
    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    log_level: str = "INFO"

    @property
    def llm(self) -> str:
        if self.llm_provider.lower() == "openrouter":
            return self.openrouter_model
        return self.ollama_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
