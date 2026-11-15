import re

from app.platforms.base import Platform, PlatformError, PublishedPost


class Telegram(Platform):
    name = "Telegram"
    required = ("telegram_bot_token", "telegram_chat_id")

    async def publish(self, message: str) -> PublishedPost:
        base = "https://api.telegram.org/bot" + self.credential("telegram_bot_token")
        # Check the destination before sending: private chats cannot meet public-access intent.
        chat = await self.request("POST", base + "/getChat", json={"chat_id": self.settings.telegram_chat_id})
        if not chat.get("ok"):
            raise PlatformError("Telegram chat lookup failed")
        destination = chat["result"]
        username = destination.get("username", "")
        if destination.get("type") != "channel" or not re.fullmatch(r"[A-Za-z0-9_]+", username):
            raise PlatformError("Telegram destination must be a public channel with a username")
        data = await self.request(
            "POST",
            base + "/sendMessage",
            json={"chat_id": destination["id"], "text": message, "link_preview_options": {"is_disabled": False}},
        )
        if not data.get("ok"):
            raise PlatformError("Telegram rejected message")
        return PublishedPost(f"https://t.me/{username}/{data['result']['message_id']}", True)
