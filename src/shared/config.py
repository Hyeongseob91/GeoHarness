from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_MAPS_KEY: str = ""
    GEMINI_API_KEY: str = ""
    NAVER_CLIENT_ID: str = ""            # NCP (지도 렌더링 + Geocoding 폴백)
    NAVER_CLIENT_SECRET: str = ""
    NAVER_MAP_CLIENT_ID: str = ""         # NCP Maps SDK (프론트 지도)
    NAVER_SEARCH_CLIENT_ID: str = ""     # Naver Developers (장소 검색)
    NAVER_SEARCH_CLIENT_SECRET: str = ""
    VWORLD_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
