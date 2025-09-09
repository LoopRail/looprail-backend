from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    blockradar_base_url: str

    blockradar_ethereum_wallet_id: str
    blockradar_ethereum_wallet_api_key: str
    
    treasury_wallet_id: str
    
    paycrest_base_url: str
    paycrest_api_key: str
    
    database_hostname: str
    database_port: int
    database_password: str
    database_name: str
    database_username: str
    
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
settings = Settings() # type: ignore
