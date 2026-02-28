from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_MAPS_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
