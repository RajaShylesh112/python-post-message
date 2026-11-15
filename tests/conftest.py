import json

import httpx
import pytest

from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        devto_api_key="test-dev",
        wordpress_access_token="test-wp",
        wordpress_site_id="123",
        mastodon_access_token="test-masto",
        bluesky_identifier="tester.bsky.social",
        bluesky_app_password="test-app",
        telegram_bot_token="test-bot",
        telegram_chat_id="@testchannel",
    )


def successful_response(request):
    path = request.url.path
    body = json.loads(request.content) if request.content else {}
    if path == "/api/articles":
        assert body["article"]["published"] is True
        return httpx.Response(201, json={"url": "https://dev.to/test/demo", "published": True})
    if request.url.host == "public-api.wordpress.com":
        if request.method == "GET":
            return httpx.Response(200, json={"is_private": False})
        assert body["status"] == "publish"
        assert '<a href="https://example.com">' in body["content"]
        return httpx.Response(200, json={"URL": "https://test.wordpress.com/demo", "status": "publish"})
    if path == "/api/v1/statuses":
        assert body["visibility"] == "public"
        return httpx.Response(200, json={"url": "https://mastodon.social/@test/1", "visibility": "public"})
    if path.endswith("createSession"):
        return httpx.Response(200, json={"did": "did:plc:test", "accessJwt": "test-jwt"})
    if path.endswith("createRecord"):
        facet = body["record"]["facets"][0]
        span = facet["index"]
        assert body["record"]["text"].encode()[span["byteStart"] : span["byteEnd"]].decode() == "https://example.com"
        return httpx.Response(200, json={"uri": "at://did:plc:test/app.bsky.feed.post/abc"})
    if path.endswith("getChat"):
        return httpx.Response(
            200, json={"ok": True, "result": {"id": -100123, "type": "channel", "username": "testchannel"}}
        )
    if path.endswith("sendMessage"):
        assert body["chat_id"] == -100123
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})
    raise AssertionError(f"Unexpected test route: {path}")
