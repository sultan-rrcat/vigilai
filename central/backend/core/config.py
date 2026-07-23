from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class CentralSettings(BaseSettings):
    DB_HOST: str
    DB_HOST_PORT: int
    DB_NAME: str
    DB_USER: str 
    DB_PASSWORD: str
    KAFKA_BROKER: str
    
    model_config = SettingsConfigDict(
        env_file = "../.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @computed_field
    @property

    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_HOST_PORT}"
            f"/{self.DB_NAME}"
        )

settings = CentralSettings()