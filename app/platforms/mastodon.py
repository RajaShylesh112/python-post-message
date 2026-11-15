from app.platforms.base import Platform, PublishedPost


class Mastodon(Platform):
    name = "Mastodon"
    required = ("mastodon_access_token",)

    async def publish(self, message: str) -> PublishedPost:
        data = await self.request(
            "POST",
            str(self.settings.mastodon_base_url).rstrip("/") + "/api/v1/statuses",
            headers={"Authorization": "Bearer " + self.credential("mastodon_access_token")},
            json={"status": message, "visibility": "public"},
        )
        return PublishedPost(data["url"], data["visibility"] == "public")
