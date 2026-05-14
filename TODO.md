# Roadmap

Tracks features deferred beyond the initial REST-only release.

## v0.1.0 — URL-embedded bearer (`?apikey=` style)

Support the Alpha Vantage / many-public-MCP-servers convention where the
bearer is passed as a query-string parameter, e.g.:

```
https://kraken.beheydt.dev/mcp?apikey=YOUR_API_KEY
```

Goal is UX parity with that ecosystem: a user can paste a single URL
into an MCP client and be connected, no separate "Authorization header"
config step. Needed in practice because Claude Desktop's remote-MCP
config does not currently let users set an Authorization header, so
without this the bearer auth is unreachable from that client.
Internally it routes through the **same `TokenVerifier`** as
`Authorization: Bearer …` — it's only an alternate transport for the
same credential, not a second auth mechanism.

- [x] Middleware that lifts `?apikey=…` into a synthetic
      `Authorization: Bearer …` header before FastMCP sees the request
      (`_ApiKeyQueryMiddleware` in `server.py`)
- [x] Strip the param from the URL before the inner app sees it — the
      token never reaches FastMCP or its verifier in query form.
      Caveat: uvicorn's own access log runs upstream of middleware, so
      the raw request line can still appear on stdout; operators who
      need that scrubbed should reconfigure uvicorn's log format or
      have a reverse proxy strip the param. Documented in the
      middleware docstring.
- [ ] Document the trade-off in the README: query-string secrets leak
      into browser history, reverse-proxy access logs, and HTTP
      `Referer` headers — OAuth 2.1 forbids the pattern for OAuth
      access tokens, but our opaque bearer makes its own trade-off.
- [ ] Decide whether to gate this behind a server-side flag — deferred:
      not needed for the immediate Claude Desktop use case, can be
      added trivially if a compliance scenario requires header-only
      auth.

## v0.2.0 — OAuth 2.1 remote auth

Migrate the remote transport from opaque-bearer auth to the OAuth 2.1
flow mandated by the MCP 2025-06-18 authorization spec, so that Claude
connectors (Claude.ai, Claude Desktop, Claude Code) can connect without
the user pasting a bearer token by hand. The local stdio transport keeps
bypassing auth as it does today.

Direction (to be confirmed when starting the version):

- Stay on **FastMCP**, upgrade to **3.x**. The OAuth pieces
  (`OAuthProxy`, `RemoteAuthProvider`) graduated from beta in 3.0, so the
  earlier concern about FastMCP's remote layer being beta no longer
  applies.
- mcp-kraken acts as **Resource Server only** (RFC 9728 Protected
  Resource Metadata). The Authorization Server is **external** — an IdP
  with native DCR support (WorkOS AuthKit, Auth0, Stytch, Clerk, Kinde,
  …) plugged in via `RemoteAuthProvider`. Choosing the IdP is part of
  this version; the deciding criterion is "lets us bill end users later"
  since the long-term goal is to offer a hosted paid tier.
- Fallback path if we start with an IdP that lacks DCR (GitHub, Google):
  use `OAuthProxy` as a DCR shim. Lower friction to ship, but the
  identity it gives us is not a billable customer.
- Mandatory bits per spec: OAuth 2.1 + PKCE, `resource` parameter
  (RFC 8707) with strict audience validation on every request, DCR
  (RFC 7591) advertised via `.well-known`, `WWW-Authenticate` on 401
  pointing at the Protected Resource Metadata URL. No token passthrough
  — the OAuth access token from the MCP client is never forwarded to
  Kraken (Kraken uses its own API key + HMAC, already a separate trust
  boundary).
- Reuse the existing **SQLite store** (`auth/store.py`) but repurpose it:
  instead of holding hashed bearer tokens, it maps `idp_user_id` →
  Kraken API credentials + cached `GetAPIKeyInfo` permission tree
  (+ a billing customer id slot for later). Access-token validation
  itself is stateless (JWT + JWKS from the IdP), not DB-backed.
- CLI `mcp-kraken token …` stays available for headless/CI use cases
  during the transition, then is folded into [`Per-token Kraken
  credentials`](#auth--multi-tenancy) once the OAuth path is the default.

References:
- [MCP Authorization spec 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [Claude — Building custom connectors](https://claude.com/docs/connectors/building)
- [FastMCP OAuth Proxy](https://gofastmcp.com/servers/auth/oauth-proxy)
- [FastMCP Remote Auth Provider](https://gofastmcp.com/servers/auth/remote-oauth)
- RFCs: [8414](https://datatracker.ietf.org/doc/html/rfc8414),
  [7591](https://datatracker.ietf.org/doc/html/rfc7591),
  [9728](https://datatracker.ietf.org/doc/html/rfc9728),
  [8707](https://www.rfc-editor.org/rfc/rfc8707.html),
  [OAuth 2.1 draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13)

## v1.x — Transport layers

### WebSocket v2 support
- [ ] Public feeds: `ticker`, `book`, `trade`, `ohlc`, `instrument`
- [ ] Private feeds: `executions`, `balances`, `level3` (auth via `/private/GetWebSocketsToken`)
- [ ] Subscription management as MCP tools (subscribe / unsubscribe / list_active)
- [ ] Stream-to-snapshot helpers so the MCP client can read recent events without holding a long-lived stream
- [ ] Auto-reconnect with exponential backoff and token refresh
- [ ] Respect the `websocket.interface` permission flag from `GetAPIKeyInfo`
- Reference: <https://docs.kraken.com/api/docs/websocket-v2/>

### FIX protocol support
- [ ] FIX 4.4 session bring-up (logon, heartbeat, logout)
- [ ] Order entry: `NewOrderSingle`, `OrderCancelRequest`, `OrderCancelReplaceRequest`
- [ ] Execution reports & order status fan-out
- [ ] FIX-specific config (sender comp ID, target comp ID, sequence reset policy)
- [ ] Decide deployment model: in-process (slow path) vs. sidecar (recommended)
- Reference: <https://docs.kraken.com/api/docs/fix-api-trading/>

## Auth & multi-tenancy

- [ ] Per-token Kraken credentials — let each MCP bearer token bind to a different Kraken API key, instead of one shared key for the whole server
- [ ] Scope-based authorization on MCP tools (read-only token cannot call trading tools)
- [ ] Rate-limit incoming MCP requests per token (independent of Kraken rate limit)
- [ ] Optional mTLS at the reverse proxy layer

## Operations

- [ ] Prometheus `/metrics` endpoint (request count, latency, Kraken error codes)
- [ ] Structured JSON logs with request IDs that propagate to Kraken correlation headers
- [ ] Healthcheck endpoint that probes Kraken `SystemStatus`
- [ ] OpenTelemetry tracing
- [ ] Token rotation helpers in the CLI (`token rotate <id>`)
- [ ] Docker image compatibility with secrets (e.g., Docker Secrets or Kubernetes Secrets)

## Quality of life

- [ ] Pydantic response models for every Kraken endpoint (currently raw dict pass-through)
- [ ] Optional cache layer for public market-data endpoints
- [ ] Built-in pagination iterators for `ClosedOrders`, `TradeHistory`, `Ledgers`
- [ ] Replay tool: re-issue a previous order from an execution report
