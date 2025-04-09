from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "rss"
    app_title: str = "Inoreader Clone"
    
    class Config:
        env_file = ".env"

settings = Settings()