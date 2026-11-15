from datetime import datetime, timezone

from app.platforms.base import Platform, PlatformError, PublishedPost
from app.schemas import LINK

BASE = "https://bsky.social/xrpc/"


class Bluesky(Platform):
    name = "Bluesky"
    required = ("bluesky_identifier", "bluesky_app_password")

    async def publish(self, message: str) -> PublishedPost:
        session = await self.request(
            "POST",
            BASE + "com.atproto.server.createSession",
            json={"identifier": self.settings.bluesky_identifier, "password": self.credential("bluesky_app_password")},
        )
        match = LINK.search(message)
        url = match.group().rstrip(".,!;:)]}")
        start = len(message[: match.start()].encode("utf-8"))
        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": [
                {
                    "index": {"byteStart": start, "byteEnd": start + len(url.encode("utf-8"))},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
                }
            ],
        }
        data = await self.request(
            "POST",
            BASE + "com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
        )
        prefix = f"at://{session['did']}/app.bsky.feed.post/"
        if not data["uri"].startswith(prefix):
            raise PlatformError("Unexpected Bluesky record URI")
        key = data["uri"][len(prefix) :]
        return PublishedPost(f"https://bsky.app/profile/{session['did']}/post/{key}", True)
