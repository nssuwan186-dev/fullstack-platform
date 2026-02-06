from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "FullStack Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "fullstack_db"
    
    # ถ้าไม่มีค่า ENV ให้ใช้ SQLite อัตโนมัติ (Fallback)
    USE_SQLITE: bool = True 

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.USE_SQLITE and not os.getenv("POSTGRES_SERVER"):
             return "sqlite+aiosqlite:///./local_dev.db"
        
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        ))

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
