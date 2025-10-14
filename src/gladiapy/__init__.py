"""
Compatibility package that re-exports gladiapp under the gladiapy name.
This allows example imports like `from gladiapy.v2 import ...` to work
without renaming the underlying package structure.
"""

from .v2 import *  # re-export symbols from v2
try:
    from .v2 import __all__ as __all__  # type: ignore
except Exception:
    __all__ = []
"""Python client for Gladia API.

This package mirrors the structure of the C++ gladiapy library with:
- v2.GladiaRestClient for REST endpoints
- v2.ws.GladiaWebsocketClient and GladiaWebsocketClientSession for WebSocket

Public API entry points are under gladiapy.v2 and gladiapy.v2.ws
"""

from .v2 import *  # re-export

__all__ = ["v2"]
