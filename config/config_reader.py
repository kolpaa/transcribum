from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, DirectoryPath


class Settings(BaseSettings):
    TG_BOT_TOKEN: SecretStr
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    WHISPER_DEVICE: str
    WHISPER_MODEL: str

    DOWNLOADS_DIR: DirectoryPath = DirectoryPath("./data/downloads")
    TRANSCRIPTS_DIR: DirectoryPath = DirectoryPath("./data/transcripts")

    model_config = SettingsConfigDict(env_file='config/.env', env_file_encoding='utf-8')
    
    def get_db_url(self):
        return (f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")


config = Settings()