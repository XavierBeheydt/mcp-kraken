# Roadmap

Tracks features deferred beyond the initial REST-only release.

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

## Documentation

- [ ] Move Github Page in `docs/page` or `page` folder path
