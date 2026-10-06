from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str
    JWT_SECRET_KEY:str
    JWT_ALGORITHM:str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES:int
    ADMIN_NAME:str
    ADMIN_EMAIL:str
    ADMIN_PASSWORD:str

    DOCUMENT_UPLOAD_DIR: str
    DOCUMENT_EXTRACTED_DIR:str

    REDIS_URL: str

    MAX_UPLOAD_SIZE_MB: int

    INFERENCE_MODE: str = "local"

    COHERE_API_KEY: str | None = None

    COHERE_EMBEDDING_MODEL: str = "embed-english-light-v3.0"

    COHERE_RERANKER_MODEL: str = "rerank-english-v3.0"



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()