from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core Application Settings
    APP_NAME: str = "Autonomous Marketing Ecosystem"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Infrastructure Configuration
    RABBITMQ_URL: str = "amqp://user:password@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "marketing_nervous_system"

    POSTGRES_URL: str = "postgresql://user:password@localhost:5432/autonomous_marketing"

    REDIS_URL: str = "redis://localhost:6379/0"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LLM_MODEL: str = "qwen2.5"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 3

    # System Governance / Paths
    TOOL_FORGE_DIR: str = "src/tools/generated"
    AUDIT_INTERVAL_SECONDS: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

# Global settings instance
settings = Settings()
