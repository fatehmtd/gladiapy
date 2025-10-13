"""Python client for Gladia API.

This package mirrors the structure of the C++ gladiapp library with:
- v2.GladiaRestClient for REST endpoints
- v2.ws.GladiaWebsocketClient and GladiaWebsocketClientSession for WebSocket

Public API entry points are under gladiapp.v2 and gladiapp.v2.ws
"""

from .v2 import *  # re-export

__all__ = ["v2"]
