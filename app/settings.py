# app/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_KEY: str  # Define the environment variable you expect

    class Config:
        env_file = ".env"  # Load environment variables from .env file

settings = Settings()  # This will load the .env variables into the Settings class
