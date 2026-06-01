"""bv — minimal agentic library for BrainVoyager UI automation.

Two functions only:
    query()  → snapshot the focused window's widget tree
    act()    → click a widget or invoke a method on it

Prerequisite: bv_inject.dylib must be loaded into BrainVoyager with
    DYLD_INSERT_LIBRARIES=./bv_inject.dylib \
        /Applications/BrainVoyager.app/Contents/MacOS/BrainVoyager

Inspired by qt-widgeteer (https://github.com/AurynRobotics/qt-widgeteer).
"""

import json
import websocket

DEFAULT_PORT = 9000
DEFAULT_TIMEOUT = 10


def _connect(port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    return websocket.create_connection(f"ws://localhost:{port}", timeout=timeout)


def _send(ws, cid, command, params=None):
    msg = {"type": "command", "id": str(cid), "command": command, "params": params or {}}
    ws.send(json.dumps(msg))
    return json.loads(ws.recv())


def _pick_window(windows, window_title=None):
    """Pick a window from the list by optional title filter, then by active flag."""
    if window_title:
        wlower = window_title.lower()
        match = next(
            (w for w in windows
             if wlower in w.get("windowTitle", "").lower()
             or wlower in w.get("className", "").lower()),
            None,
        )
        if match:
            return match
    active = next((w for w in windows if w.get("isActiveWindow")), None)
    if active:
        return active
    return windows[0] if windows else None


def query(window_title=None, port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """Return the widget tree of the currently focused window.

    If *window_title* is given, match against window title or class name
    (case-insensitive partial match) instead of using the active window.

    Returns a dict with keys: title, class, objectName, tree.

    Example:
        info = bv.query()
        info["title"]              # 'BrainVoyager'
        info["tree"]["children"]   # list of top-level widgets

        info = bv.query("Volume")  # query the 3D Volume Tools dialog
    """
    ws = _connect(port, timeout)
    try:
        r = _send(ws, 1, "list_windows")
        windows = r.get("result", {}).get("windows", [])
        target = _pick_window(windows, window_title)

        if not target:
            return {"title": "", "class": "", "objectName": "", "tree": {}}

        selector = target.get("selector", "")
        r = _send(ws, 2, "get_tree", {"depth": 99, "root": selector} if selector else {"depth": 5})
        tree = r.get("result", {})
        return {
            "title": target.get("windowTitle", ""),
            "class": target.get("className", ""),
            "objectName": target.get("objectName", ""),
            "tree": tree,
        }
    finally:
        ws.close()


def act(target, action="click", port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """Apply an action to a widget.

    Args:
        target: Widget selector ("@text:Open", "@name:spin", "@class:QPushButton")
        action: "click" or a method name like "stepUp", "setText", "toggle"

    Returns:
        True if the action succeeded.

    Example:
        bv.act("@text:Open")                             # click a button
        bv.act("@name:m_XCoord", "stepUp")                # invoke method
    """
    ws = _connect(port, timeout)
    try:
        if action == "click":
            r = _send(ws, 1, "click", {"target": target})
        else:
            r = _send(ws, 1, "invoke", {"target": target, "method": action})
        return r.get("success", False)
    except Exception:
        return False
    finally:
        ws.close()


# ── BV coordinate system spinbox names ────────────────────────────────────

_COORD_SPINBOXES = {"x": "m_XCoord", "y": "m_YCoord", "z": "m_ZCoord"}


def step_coord(axis, direction, n=1, port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """Step the crosshair along *axis* ("x" / "y" / "z").

    Args:
        axis: "x", "y", or "z"
        direction: "up" (stepUp / increase) or "down" (stepDown / decrease)
        n: Number of steps (default 1)

    Returns:
        True if all steps succeeded.
    """
    name = _COORD_SPINBOXES.get(axis.lower())
    if not name:
        return False
    method = "stepUp" if direction == "up" else "stepDown"
    target = f"@name:{name}"

    ws = _connect(port, timeout)
    try:
        for _ in range(n):
            r = _send(ws, 1, "invoke", {"target": target, "method": method})
            if not r.get("success", False):
                return False
        return True
    except Exception:
        return False
    finally:
        ws.close()


def list_windows(port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """Return a list of all accessible windows.

    Each window is a dict with: windowTitle, className, objectName,
    selector, isActiveWindow, isModal, geometry.
    """
    ws = _connect(port, timeout)
    try:
        r = _send(ws, 1, "list_windows")
        return r.get("result", {}).get("windows", [])
    finally:
        ws.close()
