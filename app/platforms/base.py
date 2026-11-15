from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import Settings


class PlatformError(Exception):
    """Safe, fixed error text that never includes upstream bodies or credentials."""


@dataclass(frozen=True)
class PublishedPost:
    url: str
    public: bool


class Platform(ABC):
    name: str
    required: tuple[str, ...]

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    def credential(self, name: str) -> str:
        value = getattr(self.settings, name)
        return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)

    def check_configuration(self) -> None:
        missing = [key.upper() for key in self.required if not self.credential(key)]
        if missing:
            raise PlatformError("Missing configuration: " + ", ".join(missing))

    async def request(self, method: str, url: str, **kwargs) -> dict:
        response = await self.client.request(method, url, **kwargs)
        if response.status_code >= 400:
            if response.status_code in (401, 403):
                raise PlatformError("Authentication or permission denied")
            if response.status_code == 429:
                raise PlatformError("Platform rate limit exceeded; retry later")
            raise PlatformError(f"Platform HTTP error ({response.status_code})")
        data = response.json()
        if not isinstance(data, dict):
            raise PlatformError("Invalid platform response")
        return data

    @abstractmethod
    async def publish(self, message: str) -> PublishedPost: ...
