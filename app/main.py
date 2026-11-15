import logging
import secrets
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import Settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import post_message

# HTTPX INFO logs include full URLs; Telegram embeds a token in its URL.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = Settings()
    async with httpx.AsyncClient(
        timeout=app.state.settings.http_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "python-post-message/1.0"},
    ) as client:
        app.state.client = client
        yield


app = FastAPI(
    title="Automated Multi-Platform Posting",
    version="1.0.0",
    lifespan=lifespan,
    description="Publishes to five internally selected platforms. Result timestamps are UTC.",
)
key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def authorize(key: str | None = Security(key_header)) -> None:
    expected = app.state.settings.posting_api_key.get_secret_value()
    if expected and (key is None or not secrets.compare_digest(key.encode(), expected.encode())):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.post("/posting", response_model=PostingResponse, dependencies=[Depends(authorize)])
async def posting(body: PostingRequest) -> PostingResponse:
    """200 includes independent platform outcomes; success means at least one published.

    Validation errors return 422 before any platform calls. No automatic POST retries.
    """
    return await post_message(body.message, app.state.settings, app.state.client)
