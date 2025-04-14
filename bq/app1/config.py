from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "rss"
    app_title: str = "Inoreader Clone"
    debug: bool = False
    log_level: str = "INFO"
    
    # Add these new settings for better configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'  # Add encoding for Windows compatibility
        case_sensitive = False  # Allow case-insensitive env vars

settings = Settings()