from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    DATABASE_URL: str = "sqlite:///./barberia.db"
    SECRET_KEY: str = "cambia-esto-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    class Config:
        env_file = ".env"


config = Settings()
