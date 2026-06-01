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


def query(port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """Return the widget tree of the currently focused window.

    Returns a dict with keys: title, class, objectName, tree.

    Example:
        info = bv.query()
        info["title"]              # 'BrainVoyager'
        info["tree"]["children"]   # list of top-level widgets
    """
    ws = _connect(port, timeout)
    try:
        r = _send(ws, 1, "list_windows")
        windows = r.get("result", {}).get("windows", [])
        active = next((w for w in windows if w.get("isActiveWindow")), None)
        if active is None and windows:
            active = windows[0]

        if not active:
            return {"title": "", "class": "", "objectName": "", "tree": {}}

        selector = active.get("selector", "")
        r = _send(ws, 2, "get_tree", {"depth": 99, "root": selector} if selector else {"depth": 5})
        tree = r.get("result", {})
        return {
            "title": active.get("windowTitle", ""),
            "class": active.get("className", ""),
            "objectName": active.get("objectName", ""),
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
        bv.act("@text:Open")                   # click a button
        bv.act("@name:m_ZCoordMiniTools", "stepUp")  # invoke method
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
