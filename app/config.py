from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_minutes: int = Field(default=30, ge=1, le=120)
    payment_mode: str = 'mock'

    @field_validator('jwt_secret')
    @classmethod
    def secret_not_placeholder(cls, value):
        if value.startswith('SUBSTITUA'):
            raise ValueError('Gere uma chave JWT aleatória antes de executar.')
        return value

    @field_validator('payment_mode')
    @classmethod
    def only_mock(cls, value):
        if value != 'mock':
            raise ValueError('Este MVP só implementa o modo mock.')
        return value

@lru_cache
def settings():
    return Settings()
