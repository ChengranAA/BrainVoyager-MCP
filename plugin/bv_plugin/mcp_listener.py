"""BrainVoyager MCP Listener — non-blocking TCP server with hash-table dispatch.

Paste this entire script into BrainVoyager's Python Plugin editor and run it.
"""

import socket
import json
import os
import sys

# Make sure listener_handlers/ is importable (BV may not auto-discover packages)
sys.path.insert(0, os.getcwd())

# BV injects `bv` into the global namespace.  We pass it explicitly into the
# handler modules so they don't rely on implicit globals.
from listener_handlers import set_bv, ALL_HANDLERS
set_bv(bv)

# BrainVoyager uses different Qt wrappers — try all three.
try:
    from PyQt5.QtCore import QTimer
except ImportError:
    try:
        from PySide2.QtCore import QTimer
    except ImportError:
        from PySide6.QtCore import QTimer


HOST = "127.0.0.1"
PORT = 5050

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
server_socket.setblocking(False)

bv.print_to_log(f"SUCCESS: Real-time listener active on {HOST}:{PORT}")


def check_for_mcp_requests():
    """Called by QTimer every 100 ms.  Accepts one connection, dispatches it."""
    client_socket = None
    try:
        client_socket, address = server_socket.accept()
        client_socket.settimeout(1.0)
        request = client_socket.recv(2048).decode("utf-8")

        body = request.split("\r\n\r\n")[-1]
        data = json.loads(body)
        action = data.get("action", "")

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
        pass
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


mcp_timer = QTimer()
mcp_timer.timeout.connect(check_for_mcp_requests)
mcp_timer.start(100)
