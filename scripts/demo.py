"""Reproducible offline demo. All upstream calls intercepted; nothing is published."""

import json
import logging
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from tests.conftest import successful_response

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence"
MESSAGE = "Grow your business 🚀 https://example.com"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print("OFFLINE DEMO: simulated upstream responses; no real posts or credentials.")
    settings = Settings(
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
    with TestClient(app) as client:
        original = app.state.client
        app.state.settings = settings
        mock = httpx.AsyncClient(transport=httpx.MockTransport(successful_response))
        app.state.client = mock
        try:
            response = client.post("/posting", json={"message": MESSAGE})
            assert response.status_code == 200 and response.json()["success"]
            (OUT / "simulated-success.json").write_text(json.dumps(response.json(), indent=2) + "\n")
            print("POST /posting -> 200; all five simulated publications succeeded")

            def mixed(request):
                if request.url.host == "dev.to":
                    return httpx.Response(401, json={"error": "example rejected credential"})
                return successful_response(request)

            client.portal.call(mock.aclose)
            mock = httpx.AsyncClient(transport=httpx.MockTransport(mixed))
            app.state.client = mock
            response = client.post("/posting", json={"message": MESSAGE})
            assert sum(r["status"] == "success" for r in response.json()["results"]) == 4
            (OUT / "simulated-partial-failure.json").write_text(json.dumps(response.json(), indent=2) + "\n")
            print("POST /posting -> 200; DEV rejected; other four simulated publications succeeded")
            response = client.post("/posting", json={"message": "Missing CTA"})
            assert response.status_code == 422
            (OUT / "validation-error.json").write_text(json.dumps(response.json(), indent=2) + "\n")
            print("POST /posting with missing CTA -> 422; no upstream requests")
        finally:
            client.portal.call(mock.aclose)
            app.state.client = original


if __name__ == "__main__":
    main()
