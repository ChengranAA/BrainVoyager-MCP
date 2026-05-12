"""BrainVoyager MCP Listener — non-blocking TCP server with hash-table dispatch.

Paste this entire script into BrainVoyager's Python Plugin editor and run it.
It uses Qt's event loop (QTimer) to poll a non-blocking TCP socket, so BV
stays responsive while continuously listening for MCP server commands.

Architecture (Option A-Lite, industry standard):
    MCP client → one of 3 servers → HTTP POST → THIS LISTENER → dispatch table
                                                              ↓
                                                   ALL_HANDLERS[action](data)
                                                              ↓
                                                   bv.some_command(…)

The if/elif chain is gone.  Every action maps to a handler function via a
plain Python dict — O(1) lookup, zero branching.

Adding a new action:
    1. Add a handler function to the appropriate listener_handlers/ module.
    2. Add ``"action_name": handler_func`` to that module's HANDLERS dict.
    3. Done — the listener picks it up automatically.
"""

import socket
import json

# BrainVoyager uses different Qt wrappers — try all three.
try:
    from PyQt5.QtCore import QTimer
except ImportError:
    try:
        from PySide2.QtCore import QTimer
    except ImportError:
        from PySide6.QtCore import QTimer

from listener_handlers import ALL_HANDLERS

# ---------------------------------------------------------------------------
# Non-blocking TCP server setup
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 5050

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
server_socket.setblocking(False)  # CRITICAL — prevents UI freeze

bv.print_to_log(f"SUCCESS: Real-time listener active on {HOST}:{PORT}")

# ---------------------------------------------------------------------------
# Request dispatcher — O(1) hash-table lookup, zero if/elif branching
# ---------------------------------------------------------------------------

def check_for_mcp_requests():
    """Called by QTimer every 100 ms.  Accepts one connection, dispatches it."""
    client_socket = None
    try:
        client_socket, address = server_socket.accept()
        client_socket.settimeout(1.0)
        request = client_socket.recv(2048).decode("utf-8")

        # Parse HTTP body
        body = request.split("\r\n\r\n")[-1]
        data = json.loads(body)
        action = data.get("action", "")

        # ── O(1) hash-table dispatch ──
        handler = ALL_HANDLERS.get(action)
        if handler:
            response = handler(data)
        else:
            response = (
                f"HTTP/1.1 400 Bad Request\n\n"
                f"Unknown action: '{action}'"
            )

        client_socket.sendall(response.encode("utf-8"))

    except BlockingIOError:
        pass  # No pending connection — completely normal
    except json.JSONDecodeError:
        if client_socket:
            client_socket.sendall(
                b"HTTP/1.1 400 Bad Request\n\nInvalid JSON in request body."
            )
    except Exception as e:
        bv.print_to_log(f"Listener error: {e}")
    finally:
        try:
            if client_socket:
                client_socket.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Hijack Qt's event loop — poll every 100 ms
# ---------------------------------------------------------------------------

mcp_timer = QTimer()
mcp_timer.timeout.connect(check_for_mcp_requests)
mcp_timer.start(100)
