# Platform research

Reviewed on 15 November 2026. These are supported publishing APIs, not LLM completion endpoints: an LLM response alone does not create publicly accessible content. The requirement is met with five third-party publishing destinations; it does not mandate a particular LLM vendor.

| Platform / official documentation | Implemented operations | Authentication / publication evidence |
|---|---|---|
| [DEV / Forem](https://developers.forem.com/api/v1#tag/articles/operation/createArticle) | `POST https://dev.to/api/articles`; `article.title`, `body_markdown`, `published: true` | `api-key` header. Uses returned `url`; article publishing setting indicates public content. |
| [WordPress.com create post](https://developer.wordpress.com/docs/api/1.1/post/sites/%24site/posts/new/), [site metadata](https://developer.wordpress.com/docs/api/1.1/get/sites/%24site/), [OAuth](https://developer.wordpress.com/docs/oauth2/) | `GET /rest/v1.1/sites/{site}` before `POST /rest/v1.1/sites/{site}/posts/new`; `title`, escaped HTML `content`, `status: publish`, `type: post` | OAuth bearer token. Requires `is_private: false`, then returned `status: publish` and `URL`. |
| [Mastodon statuses](https://docs.joinmastodon.org/methods/statuses/#create) | `POST /api/v1/statuses`; `status`, `visibility: public` | OAuth bearer token with `write:statuses`; reads returned `url` and `visibility`. |
| [Bluesky create session](https://docs.bsky.app/docs/api/com-atproto-server-create-session), [create record](https://docs.bsky.app/docs/api/com-atproto-repo-create-record), [posting and facets](https://docs.bsky.app/docs/advanced-guides/posts) | `com.atproto.server.createSession`, then `com.atproto.repo.createRecord`; repository DID, `app.bsky.feed.post`, text, UTC `createdAt`, link facet | App password obtains short-lived `accessJwt`. Record URI is checked against account DID and collection; acknowledgement key builds `bsky.app/profile/{did}/post/{key}`. Facet positions use UTF-8 bytes, including emoji correctly. |
| [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage), [getChat](https://core.telegram.org/bots/api#getchat) | `getChat`, then `sendMessage` with chat ID/text | Bot token in URL path. Requires a public channel username, builds `https://t.me/{username}/{message_id}` only after `ok: true`. |

All adapters send JSON via HTTPX, enforce timeouts, reject redirects, and isolate upstream failures. CTA URLs are content only, never outbound request targets. Only Mastodon's trusted operator configuration changes an API origin.

## Why WordPress.com replaced Hashnode

During research `https://gql.hashnode.com` returned a 301 redirect to Hashnode's announcement. The [official announcement](https://hashnode.com/changelog/2026-05-13-graphql-api-paid-access) states that free GraphQL API access has retired and both reading and publishing require Pro. The submission therefore uses WordPress.com instead of assuming the historical free endpoint is usable.

Documentation pages for DEV, WordPress.com, Mastodon, Bluesky, and Telegram were accessible during research. Credentials and owned destinations are still required to establish live end-to-end success. Automated tests validate request construction and response handling against controlled responses, not current account permissions or live platform behavior.
