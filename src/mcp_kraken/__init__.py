"""MCP server exposing the Kraken cryptocurrency exchange REST API."""

from __future__ import annotations

try:
    from ._version import __version__
except ImportError:  # not built yet (editable from non-git checkout)
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
