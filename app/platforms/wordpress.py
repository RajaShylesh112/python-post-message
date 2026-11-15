from html import escape
from urllib.parse import quote

from app.platforms.base import Platform, PlatformError, PublishedPost
from app.schemas import LINK


class WordPress(Platform):
    name = "WordPress.com"
    required = ("wordpress_access_token", "wordpress_site_id")

    async def publish(self, message: str) -> PublishedPost:
        base = "https://public-api.wordpress.com/rest/v1.1/sites/" + quote(self.settings.wordpress_site_id, safe="")
        headers = {"Authorization": "Bearer " + self.credential("wordpress_access_token")}
        site = await self.request("GET", base, headers=headers)
        if site.get("is_private") is not False:
            raise PlatformError("WordPress destination must be a confirmed public site")
        match = LINK.search(message)
        url = match.group().rstrip(".,!;:)]}")
        # Escape all input before adding one clickable CTA; no user HTML executes.
        content = (
            escape(message[: match.start()])
            + f'<a href="{escape(url, quote=True)}">{escape(url)}</a>'
            + escape(message[match.start() + len(url) :])
        )
        data = await self.request(
            "POST",
            base + "/posts/new",
            headers=headers,
            json={
                "title": message.strip().splitlines()[0][:100],
                "content": content,
                "status": "publish",
                "type": "post",
            },
        )
        if data.get("status") != "publish":
            raise PlatformError("WordPress did not publish the post; check account permissions")
        return PublishedPost(data["URL"], True)
