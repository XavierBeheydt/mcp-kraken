"""Tools that interact with the WebSocket authentication endpoint.

The MCP itself does not (yet) ride WebSocket transports — see TODO.md. This
endpoint is exposed so a downstream client can obtain a WS token via the MCP.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..kraken import KrakenClient


def register(mcp: FastMCP, client: KrakenClient) -> None:
    @mcp.tool(tags={"private", "websocket"})
    async def get_websockets_token() -> Any:
        """Issue a token for use with the private WebSocket API.

        Tokens are valid for 15 minutes from issue. Re-issue before expiry.
        Requires the API key to have the WebSocket interface permission enabled.
        """
        return await client.private("GetWebSocketsToken")
