import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

# Count link-like tokens, including unsupported schemes, before URL validation.
LINK = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>]+", re.IGNORECASE)
HTTP_URL = TypeAdapter(HttpUrl)


class PostingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=200, strict=True)

    @field_validator("message")
    @classmethod
    def exactly_one_cta(cls, value: str) -> str:
        links = LINK.findall(value)
        if len(links) != 1:
            raise ValueError("Message must contain exactly one absolute HTTP(S) CTA URL")
        url = links[0].rstrip(".,!;:)]}")
        try:
            parsed = HTTP_URL.validate_python(url)
            parts = urlsplit(url)
            if not parts.netloc or parsed.username or parsed.password:
                raise ValueError("Invalid CTA URL")
        except ValueError as exc:
            raise ValueError("CTA must be a valid HTTP(S) URL without credentials") from exc
        return value


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
