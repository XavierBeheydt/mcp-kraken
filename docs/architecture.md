# Architecture notes

How the pieces fit together, and the traps that are not obvious from the
code. User-facing documentation (install, configuration, tool list) lives in
the [README](../README.md); the target architecture of the ongoing
reorientation is in [PLAN.md](../PLAN.md).

## Module map

```
src/mcp_kraken/
├── __init__.py __main__.py cli.py config.py logging.py server.py
├── auth/          # bearer-token store (SQLite), FastMCP TokenVerifier
├── kraken/        # async REST client, HMAC signing, errors, permission map
└── tools/         # MCP tool registrations, one module per Kraken category
tests/             # pytest; respx mocks the Kraken HTTP surface
docker/            # Dockerfile + compose.yml (build context is the repo root)
.github/workflows/ # test, develop-publish, release, pages, codeql
docs/              # GitHub Pages site + contributor documentation
```

Single process, stateless apart from the SQLite token store.

## Two authentication boundaries

They are independent and must not be conflated:

| Boundary                               | Mechanism                                    |
| -------------------------------------- | -------------------------------------------- |
| MCP client → mcp-kraken (you control)   | Opaque bearer tokens, SHA-256 hashed in SQLite |
| mcp-kraken → Kraken                     | `KRAKEN_API_KEY` + HMAC-SHA512 request signature |

Bearer tokens are minted with `mcp-kraken token create NAME [--expires-in 90d]`,
printed once, and only their hash is stored. `token list` shows ids only;
`token revoke ID` flags one as revoked.

`Authorization: Bearer …` and the `?apikey=…` query alias route through the
same `TokenVerifier` — the query form is a transport convenience for clients
that cannot set headers, not a second credential. The **stdio** transport
bypasses the bearer layer entirely: such sessions are local by construction.

Kraken credentials never come from an MCP request. They are read from the
environment (or a Docker secret) at startup.

## Kraken API key permissions

On the first private call the client probes `/private/GetAPIKeyInfo`, parses
the returned permission tree and caches it. Later calls check their required
permission against that cache and fail early with `KrakenPermissionError`.
The endpoint → permission mapping lives in
`kraken/permissions.py::PERMISSION_REQUIREMENTS`; adding a tool means adding
its endpoint there.

**Fallback.** In some regions and on some accounts `GetAPIKeyInfo` answers
`EGeneral:Unknown method`. `KrakenClient.get_permissions` catches that, logs
a warning, and lets Kraken enforce permissions over the wire instead.

## Traps

- **`list[T] | None = None` tool parameters lose their JSON-schema
  `type: array`** in the schema FastMCP exposes over MCP. Clients then send
  the value as a JSON-encoded string, which Pydantic strict mode rejects. Use
  `Annotated[list[T], Field(default_factory=list)]` (with `# noqa: B008`), or
  another idiom that keeps Pydantic from collapsing the type.
- **Kraken reports errors as `200 OK` with a non-empty `error` array**, not
  as HTTP error codes. `KrakenClient._unwrap` classifies them — when a new
  error category shows up, extend `errors.classify`, never the call sites.
- **Order- and funds-moving tools are dangerous** (`add_order`,
  `cancel_order`, `withdraw`, `wallet_transfer`, `allocate_earn`, …). Never
  exercise them against real credentials in tests or documentation without an
  explicit opt-in.
- **uvicorn's access log runs upstream of the middleware**, so a raw request
  line containing `?apikey=…` can still reach stdout. Operators who need that
  scrubbed reconfigure uvicorn's log format or strip the parameter in a
  reverse proxy.

## See also

- [README](../README.md) — install, configuration, tools, Docker.
- [PLAN.md](../PLAN.md) — where this architecture is heading.
- [contributing/](contributing/) — branching, releases, conventions.
