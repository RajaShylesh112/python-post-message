import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.schemas import PostingRequest
from app.services.posting_service import post_message
from tests.conftest import successful_response

MESSAGE = "Grow your business 🚀 https://example.com"


@pytest.mark.parametrize(
    "message",
    [
        "",
        "no link",
        "a" * 201,
        "Visit www.example.com",
        "Visit ftp://example.com",
        "Visit https://",
        "Visit https://user:pass@example.com",
        "https://example.com https://other.com",
        "https://example.com ftp://other.com",
        123,
        None,
    ],
)
def test_invalid_messages(message):
    with TestClient(app) as client:
        response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "message", [MESSAGE, "Go https://example.com/path?q=1&b=two#section.", "a" * 180 + " https://example.com"]
)
def test_valid_messages(message):
    assert PostingRequest(message=message).message == message


def test_platform_selection_is_internal():
    with TestClient(app) as client:
        assert client.post("/posting", json={"message": MESSAGE, "platforms": ["DEV"]}).status_code == 422


@pytest.mark.asyncio
async def test_all_five_success(settings):
    async with httpx.AsyncClient(transport=httpx.MockTransport(successful_response)) as client:
        result = await post_message(MESSAGE, settings, client)
    assert result.success
    assert len(result.results) == 5
    for item in result.results:
        assert item.status == "success" and item.public_access
        assert item.date and item.time and item.posted_url and item.error is None


@pytest.mark.parametrize(
    "failure,expected",
    [
        (401, "Authentication"),
        (403, "permission"),
        (429, "rate limit"),
        (500, "HTTP error"),
        ("timeout", "timed out"),
        ("network", "network"),
        ("json", "unexpected"),
        ("shape", "unexpected"),
    ],
)
@pytest.mark.asyncio
async def test_independent_failure_and_redaction(settings, failure, expected):
    def handler(request):
        if request.url.host == "dev.to":
            if failure == "timeout":
                raise httpx.ReadTimeout("secret-body", request=request)
            if failure == "network":
                raise httpx.ConnectError("secret-body", request=request)
            if failure == "json":
                return httpx.Response(200, text="secret-body")
            if failure == "shape":
                return httpx.Response(200, json={})
            return httpx.Response(failure, json={"message": "secret-body"})
        return successful_response(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await post_message(MESSAGE, settings, client)
    assert result.success
    assert result.results[0].status == "failed"
    assert expected in result.results[0].error
    assert "secret-body" not in result.model_dump_json()
    assert all(item.status == "success" for item in result.results[1:])
    assert result.results[0].date is None and result.results[0].posted_url is None


@pytest.mark.asyncio
async def test_missing_configuration_makes_no_requests():
    def no_network(request):
        pytest.fail("Missing credentials must not trigger network calls")

    async with httpx.AsyncClient(transport=httpx.MockTransport(no_network)) as client:
        result = await post_message(MESSAGE, Settings(_env_file=None), client)
    assert not result.success
    assert len(result.results) == 5
    assert all("Missing configuration" in r.error for r in result.results)


@pytest.mark.asyncio
async def test_private_telegram_is_not_sent(settings):
    def handler(request):
        if request.url.path.endswith("getChat"):
            return httpx.Response(200, json={"ok": True, "result": {"type": "private", "id": 1}})
        assert not request.url.path.endswith("sendMessage")
        return successful_response(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await post_message(MESSAGE, settings, client)
    assert result.results[-1].status == "failed"
    assert "public channel" in result.results[-1].error


@pytest.mark.asyncio
async def test_private_wordpress_is_not_published(settings):
    def handler(request):
        if request.url.host == "public-api.wordpress.com":
            assert request.method == "GET"
            return httpx.Response(200, json={"is_private": True})
        return successful_response(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await post_message(MESSAGE, settings, client)
    assert result.results[1].status == "failed"
    assert "secret-body" not in result.model_dump_json()


def test_endpoint_success_and_optional_auth(settings):
    with TestClient(app) as client:
        app.state.settings = settings.model_copy(
            update={"posting_api_key": Settings(posting_api_key="test-local").posting_api_key}
        )
        original = app.state.client
        mock = httpx.AsyncClient(transport=httpx.MockTransport(successful_response))
        app.state.client = mock
        try:
            assert client.post("/posting", json={"message": MESSAGE}).status_code == 401
            response = client.post("/posting", json={"message": MESSAGE}, headers={"X-API-Key": "test-local"})
            assert response.status_code == 200
            assert response.json()["success"]
            assert len(response.json()["results"]) == 5
        finally:
            client.portal.call(mock.aclose)
            app.state.client = original


def test_openapi_contract():
    schema = app.openapi()
    assert "/posting" in schema["paths"]
    assert schema["components"]["schemas"]["PostingRequest"]["properties"]["message"]["maxLength"] == 200


def test_invalid_json():
    with TestClient(app) as client:
        assert (
            client.post("/posting", content="{broken", headers={"Content-Type": "application/json"}).status_code == 422
        )
