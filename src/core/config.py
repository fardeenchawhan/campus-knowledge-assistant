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

    DOCUMENT_UPLOAD_DIR: str = "data/documents"
    DOCUMENT_EXTRACTED_DIR: str = "data/extracted"



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()