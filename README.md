# Automated Multi-Platform Posting System

FastAPI application for the Python practical assignment. `POST /posting` validates a short message and publishes concurrently to **DEV Community, WordPress.com, Mastodon, Bluesky, and a Telegram public channel**. Platform selection is internal; a failed platform never prevents attempts to the others.

**Verification:** automated tests and an offline demonstration are included. Live publishing has **not** been verified: third-party account credentials were not supplied. The application contains real HTTP integrations, not a production mock mode. With no credentials it truthfully returns five failed configuration results. See [test logs](docs/evidence/tests.log), [offline demo logs](docs/evidence/demo.log), and [real local-server response](docs/evidence/local-unconfigured-response.json).

## Setup and execution

Requires Python **3.11+** and outbound HTTPS access.

```bash
git clone https://github.com/RajaShylesh112/python-post-message.git
cd python-post-message
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Set credentials for your own accounts in .env
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Interactive API documentation: http://localhost:4000/docs (OpenAPI: `/openapi.json`). Run commands from the repository root so `.env` loads. Environment variables override `.env`.

### Platform credentials

| Platform | Environment variables | Setup and required permissions |
|---|---|---|
| DEV Community | `DEVTO_API_KEY` | Create a DEV account; Settings → Extensions → DEV Community API Keys. Creates a published article; title is derived from the message, full message becomes the Markdown body. |
| WordPress.com | `WORDPRESS_ACCESS_TOKEN`, `WORDPRESS_SITE_ID` | Register an OAuth application and authorize your WordPress.com site with write permission. Use its numeric site ID or domain. Account must be able to publish posts. Site must be public; authenticated site metadata is checked before creating a post. WordPress.com hosted sites supported; arbitrary self-hosted WordPress installations are outside scope. |
| Mastodon | `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | On your instance, Preferences → Development → New application. Authorize `write:statuses`. Base URL must be an HTTPS origin, e.g. `https://mastodon.social`. Creates a `public` status. |
| Bluesky | `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` | Use your handle and an app password from Settings → Privacy and security → App passwords. This implementation supports accounts hosted on `bsky.social`; custom PDS hosts are outside scope. It logs in, then creates an `app.bsky.feed.post` with a clickable CTA facet. |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Create a bot using BotFather. Add it as administrator to your **public channel** with posting rights; use `@channelusername` or numeric channel ID. Checks `getChat` for channel type and public username before sending. Private chats/groups/channels are rejected. |

Unconfigured integrations remain in the result list as failed; configure all five to attempt all five publications. No platform credentials are provided or committed. Use your own accounts and content suitable for the destination's policies; DEV and WordPress are article/blog destinations rather than general advertising feeds.

`HTTP_TIMEOUT_SECONDS` (default 15, range 1–60) applies per outbound request. Optional `POSTING_API_KEY` protects the endpoint with an `X-API-Key` header. Leave it empty for the assignment's localhost example. Set it before exposing the server outside a trusted local environment, and put TLS/rate limiting at the reverse proxy.

## API examples

```bash
curl -i http://localhost:4000/posting \
  -H 'Content-Type: application/json' \
  -d '{"message":"Check out our latest business platform and grow your online visibility. https://example.com"}'
```

When `POSTING_API_KEY` is configured, add `-H "X-API-Key: $POSTING_API_KEY"` (export that variable locally; do not put real keys in source files).

Request schema is exactly `{"message": "..."}`. Extra fields such as `platforms` are rejected. Message must be a string of 1–200 Python Unicode characters, contain exactly one absolute HTTP(S) link, and have no credentials in the URL. `www.example.com`, malformed URLs, missing links, and multiple link-like tokens are rejected. Trailing sentence punctuation is excluded from the clickable URL; encode trailing punctuation if it belongs to the URL itself. URL validation is syntactic: the application never fetches the CTA, checks its availability, or follows it.

**Illustrative partial response** (fictional URLs; not evidence of live publication):

```json
{
  "success": true,
  "results": [
    {
      "platform": "DEV Community",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication or permission denied"
    },
    {
      "platform": "WordPress.com",
      "status": "success",
      "posted_url": "https://test.wordpress.com/demo",
      "public_access": true,
      "date": "2026-11-15",
      "time": "06:30:00",
      "error": null
    }
  ]
}
```

Excerpt above shows two entries for brevity; actual responses always include all five in this order: DEV, WordPress.com, Mastodon, Bluesky, Telegram. Complete captured examples: [five successes, simulated](docs/evidence/simulated-success.json), [partial failure, simulated](docs/evidence/simulated-partial-failure.json), [no credentials, real local call](docs/evidence/local-unconfigured-response.json).

- **200:** processing completed, even when every platform failed. Top-level `success` means **at least one** platform succeeded; inspect each result for complete/partial success.
- **422:** invalid request, no publishing attempts. Example request: `{"message":"Missing CTA"}`. [Captured response](docs/evidence/validation-error.json) contains FastAPI's `detail` array with `loc: ["body", "message"]` and the validation error.
- **401:** configured local API key is missing or incorrect: `{"detail":"Invalid or missing API key"}`.

`date` and `time` are UTC, measured immediately after a successful platform acknowledgement. `posted_url` comes from the API, or is constructed from the acknowledged Bluesky record / Telegram message ID. `public_access` reflects the platform's public publishing setting and destination metadata; it is **not** an independent anonymous browser availability check. Moderation, deletion, or federation delays may affect later accessibility. Failed entries have null URL/date/time and false public access.

## Tests and reproducible evidence

```bash
pip install -r requirements-dev.txt
ruff check app tests scripts
pytest -q
# Offline only: all upstream responses intercepted with HTTPX MockTransport.
python -m scripts.demo
```

The demo writes JSON examples under `docs/evidence/`; timestamps will change on rerun. No third-party messages are sent. Tests cover input boundaries, URL validation, Unicode link offsets, all five adapters, partial failures, authentication, rate limits, timeouts, malformed responses, private destination rejection, API-key protection, and missing credentials with zero network calls. CI runs the tests on Python 3.11–3.13.

## Design and limits

- `app/main.py`: FastAPI lifecycle, shared async HTTPX connection pool, optional authentication.
- `app/schemas.py`: request validation and response contract.
- `app/config.py`: typed environment configuration and secret wrappers.
- `app/platforms/`: one adapter per platform and a shared HTTP helper.
- `app/services/posting_service.py`: concurrent fan-out, isolated failures, safe error reporting.
- [API research](docs/platform-research.md): official documentation, endpoint/payload details and platform choice.

No automatic retries are used for publishing POSTs: after a timeout the platform may already have accepted the content, so retries could duplicate it. Repeated incoming requests also create new posts; this assignment version has no durable queue, idempotency store, scheduling, rollback, or cross-platform transaction. Upstream calls within a multi-step adapter are sequential, while the five adapters run concurrently. Successful posts remain published if another adapter fails.

HTTP response bodies, request headers, submitted messages, and exception strings are not logged. HTTPX/httpcore request logging is suppressed at INFO because Telegram tokens are part of its API URL. Logs record only platform name and status. Third-party errors are mapped to fixed messages rather than exposing raw bodies. `.env`, virtual environments, and caches are ignored. `.env.example` contains blank credential values only.
