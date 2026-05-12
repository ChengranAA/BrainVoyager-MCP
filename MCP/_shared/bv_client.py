"""Shared BrainVoyager TCP client.

Every MCP server (core, anatomy, fmri) uses these two functions to talk to the
listener running inside BrainVoyager.  This avoids duplicating connection logic,
error handling, and path expansion across servers.
"""

import os
import json
import requests

BV_LISTENER_URL = "http://127.0.0.1:5050"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_bv(action: str, timeout: int = 10, **kwargs) -> str:
    """POST *action* (and optional keyword params) to the BV listener.

    Path values inside *kwargs* are automatically expanded (``~/``, etc.).

    Returns a human-readable result string suitable for an MCP tool response.
    """

    payload = {"action": action}
    for key, value in kwargs.items():
        # Expand any path-like arguments that exist on disk / are directories
        if isinstance(value, str) and (
            os.path.isdir(os.path.expanduser(value))
            or os.path.isfile(os.path.expanduser(value))
        ):
            payload[key] = os.path.expanduser(value)
        else:
            payload[key] = value

    try:
        r = requests.post(BV_LISTENER_URL, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return _connection_error()
    except requests.exceptions.Timeout:
        return f"Timeout: No response from BrainVoyager within {timeout}s."

    if r.status_code == 200:
        return _extract_result(r)
    return f"Error from BrainVoyager [{r.status_code}]: {r.text}"


def call_bv_with_path(action: str, path: str, timeout: int = 10, **kwargs) -> str:
    """Like :func:`call_bv` but validates that *path* exists before sending."""
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return f"Error: Path not found: '{expanded}'."
    kwargs["path"] = expanded
    return call_bv(action, timeout=timeout, **kwargs)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _extract_result(response: requests.Response) -> str:
    """Pull the ``result`` field from a JSON response, or return raw text."""
    try:
        data = json.loads(response.text)
        return str(data.get("result", response.text))
    except (json.JSONDecodeError, ValueError):
        return response.text


def _connection_error() -> str:
    return (
        "Connection Error: Could not reach the BrainVoyager Qt listener.\n\n"
        "Make sure the listener script is running inside BrainVoyager:\n"
        "  - Open BrainVoyager → Python Plugin panel\n"
        "  - Paste mcp_listener.py → Run"
    )
