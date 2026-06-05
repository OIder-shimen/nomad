from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys — only on server, never sent to frontend
    unsplash_access_key: str = ""
    geoapify_api_key: str = ""
    amap_web_api_key: str = ""

    # Auth
    secret_key: str = "change-me-to-a-random-string-at-least-32-chars"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin"

    # Database
    database_url: str = "sqlite+aiosqlite:///./nomad.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
