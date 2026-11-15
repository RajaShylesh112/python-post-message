import asyncio
import logging
from datetime import datetime, timezone

import httpx
from pydantic import HttpUrl, TypeAdapter

from app.config import Settings
from app.platforms.base import Platform, PlatformError
from app.platforms.bluesky import Bluesky
from app.platforms.devto import DevTo
from app.platforms.wordpress import WordPress
from app.platforms.mastodon import Mastodon
from app.platforms.telegram import Telegram
from app.schemas import PlatformResult, PostingResponse

logger = logging.getLogger(__name__)
PLATFORMS = (DevTo, WordPress, Mastodon, Bluesky, Telegram)


async def publish_one(platform: Platform, message: str) -> PlatformResult:
    try:
        platform.check_configuration()
        post = await platform.publish(message)
        url = TypeAdapter(HttpUrl).validate_python(post.url)
        if url.username or url.password:
            raise PlatformError("Invalid published URL")
        now = datetime.now(timezone.utc)
        result = PlatformResult(
            platform=platform.name,
            status="success",
            posted_url=str(url),
            public_access=post.public,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
        )
    except PlatformError as exc:
        result = PlatformResult(platform=platform.name, status="failed", error=str(exc))
    except httpx.TimeoutException:
        result = PlatformResult(platform=platform.name, status="failed", error="Platform request timed out")
    except httpx.RequestError:
        result = PlatformResult(platform=platform.name, status="failed", error="Platform network request failed")
    except Exception:
        # Do not log exception repr: HTTP errors may contain tokens in request URLs.
        result = PlatformResult(
            platform=platform.name, status="failed", error="Invalid or unexpected platform response"
        )
    logger.info("platform=%s status=%s", result.platform, result.status)
    return result


async def post_message(message: str, settings: Settings, client: httpx.AsyncClient) -> PostingResponse:
    results = await asyncio.gather(*(publish_one(cls(settings, client), message) for cls in PLATFORMS))
    return PostingResponse(success=any(r.status == "success" for r in results), results=results)
