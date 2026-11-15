"""Environment-only credentials; .env is explicitly excluded from version control."""

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    devto_api_key: SecretStr = SecretStr("")
    wordpress_access_token: SecretStr = SecretStr("")
    wordpress_site_id: str = ""
    mastodon_base_url: HttpUrl = "https://mastodon.social"
    mastodon_access_token: SecretStr = SecretStr("")
    bluesky_identifier: str = ""
    bluesky_app_password: SecretStr = SecretStr("")
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""
    posting_api_key: SecretStr = SecretStr("")
    http_timeout_seconds: float = Field(default=15, ge=1, le=60)

    @field_validator("mastodon_base_url")
    @classmethod
    def secure_instance(cls, value: HttpUrl) -> HttpUrl:
        if (
            value.scheme != "https"
            or value.username
            or value.password
            or value.query
            or value.fragment
            or value.path not in ("/", "")
        ):
            raise ValueError("Mastodon must be an HTTPS origin without credentials, query or path")
        return value
