"""Entrypoint for the cognee-frontend container.

Starts the cognee UI (frontend only, backend and MCP run as their own services)
and blocks until the UI subprocess exits, forwarding its exit code.
"""

import time

import cognee

server = cognee.start_ui(
    print,
    open_browser=False,
    auto_download=True,
    start_backend=False,
    start_mcp=False,
)

if server is None:
    raise SystemExit("Failed to start cognee frontend")

while True:
    code = server.poll()
    if code is not None:
        raise SystemExit(code)
    time.sleep(1)
