from app.platforms.base import Platform, PublishedPost


class DevTo(Platform):
    name = "DEV Community"
    required = ("devto_api_key",)

    async def publish(self, message: str) -> PublishedPost:
        data = await self.request(
            "POST",
            "https://dev.to/api/articles",
            headers={"api-key": self.credential("devto_api_key")},
            json={"article": {"title": message.splitlines()[0][:100], "body_markdown": message, "published": True}},
        )
        return PublishedPost(data["url"], data.get("published", True) is True)
