"""BV UI Assistant MCP Server — live widget introspection and UI automation.

EXPERIMENTAL.  Lets an AI agent query the BrainVoyager widget tree and
click / invoke widgets via the WebSocket injection bridge (port 9000).

Prerequisite:
    DYLD_INSERT_LIBRARIES=./bv_inject.dylib \\
    /Applications/BrainVoyager.app/Contents/MacOS/BrainVoyager

Tools:
    bv_launch     — launch BrainVoyager with the injection dylib
    bv_query      — snapshot the focused window's widget tree
    bv_act        — click a widget by @text, @name, or @class selector
    bv_list_windows — list all accessible top-level windows
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_ws import query, act, list_windows, step_coord

mcp = FastMCP(
    "BrainVoyager UI Assistant (experimental)",
    instructions=(
        "Experimental live-assistant server for BV widget introspection and "
        "UI automation.  Use `bv_launch` to start BV with the injection "
        "dylib, then `bv_query` to see what the current window contains, "
        "then `bv_act` to click buttons, invoke methods, or interact with "
        "widgets.  The WebSocket injection bridge must be running on "
        "localhost:9000."
    ),
)


# ── BV launch ────────────────────────────────────────────────────────────

# Resolve paths relative to this project root (two levels up from servers/).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DYLIB_PATH = _PROJECT_ROOT / "plugin" / "bv_ui_control" / "build" / "src" / "libbv_inject.dylib"
_BV_EXECUTABLE = "/Applications/BrainVoyager.app/Contents/MacOS/BrainVoyager"


@mcp.tool()
def bv_launch(
    bv_path: str = "",
    port: int = 9000,
) -> str:
    """Launch BrainVoyager with the injection dylib loaded.

    Finds the compiled bv_inject.dylib in plugin/bv_ui_control/build/src/
    and starts BrainVoyager with DYLD_INSERT_LIBRARIES so the WebSocket
    widget bridge is available on the given port.

    IMPORTANT: After this tool returns, the agent MUST wait for the user
    to confirm that BrainVoyager has fully started before calling any
    other BV tools (bv_query, bv_act, etc.).

    Args:
        bv_path: Path to BrainVoyager.app (default:
                 /Applications/BrainVoyager.app).
        port: WebSocket port for the injection bridge (default 9000).

    Returns:
        Status message.  If the dylib is not compiled, returns
        instructions for building it.
    """
    # -- Check the dylib exists --
    if not _DYLIB_PATH.exists():
        return (
            f"Injection dylib not found at:\n"
            f"  {_DYLIB_PATH}\n\n"
            f"Please compile it first:\n"
            f"  cd {_PROJECT_ROOT / 'plugin' / 'bv_ui_control'}\n"
            f"  cmake -B build -DCMAKE_BUILD_TYPE=Release\n"
            f"  cmake --build build --parallel\n\n"
            f"Requires: CMake 3.18+, Qt 6.8+, C++17 compiler."
        )

    # -- Resolve BV executable --
    bv_app = Path(bv_path) if bv_path else Path(_BV_EXECUTABLE)
    if bv_app.is_dir() or str(bv_app).endswith(".app"):
        bv_app = bv_app / "Contents" / "MacOS" / "BrainVoyager"
    if not bv_app.exists():
        return (
            f"BrainVoyager executable not found at:\n"
            f"  {bv_app}\n\n"
            f"Specify a custom path with the bv_path argument."
        )

    # -- Launch BV with the dylib injected --
    env = os.environ.copy()
    env["DYLD_INSERT_LIBRARIES"] = str(_DYLIB_PATH.resolve())

    try:
        subprocess.Popen(
            [str(bv_app)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return f"Failed to launch BrainVoyager: {e}"

    return (
        f"BrainVoyager launched with injection dylib on port {port}.\n\n"
        f"⚠️  WAIT for the user to confirm BV has fully started before "
        f"calling bv_query, bv_act, or any other BV tool."
    )


# ── Widget introspection ──────────────────────────────────────────────────


@mcp.tool()
def bv_query(
    window_title: str = "", port: int = 9000, timeout: int = 10,
) -> str:
    """Snapshot the widget tree of the currently focused window.

    If *window_title* is non-empty, matches against window title or class
    name (case-insensitive, partial) instead of using the active window.

    Returns JSON with keys:
      - title: window title
      - class: window class name
      - objectName: Qt object name
      - tree: nested widget tree (type, text, name, class, actions, children, …)

    Each widget node may include an "actions" array listing invokable
    methods (e.g. stepUp, stepDown, click, clear, selectAll).  Pass these
    directly to `bv_act`.

    Widget selectors you can use in `bv_act`:
      @text:ButtonLabel    — match by visible text (partial)
      @name:spinBox        — match by Qt objectName
      @class:QPushButton   — match by Qt class
    """
    try:
        result = query(window_title=window_title or None,
                       port=port, timeout=timeout)
        return str(result)
    except Exception as e:
        return f"Error connecting to WebSocket bridge on port {port}: {e}"


@mcp.tool()
def bv_list_windows(
    port: int = 9000, timeout: int = 10,
) -> str:
    """List all accessible top-level windows via the injection bridge.

    Returns a JSON list; each entry has windowTitle, className, objectName,
    selector, and isActiveWindow.
    """
    try:
        windows = list_windows(port=port, timeout=timeout)
        return str(windows)
    except Exception as e:
        return f"Error: {e}"


# ── Widget interaction ────────────────────────────────────────────────────


@mcp.tool()
def bv_act(
    target: str, action: str = "click",
    port: int = 9000, timeout: int = 10,
) -> str:
    """Apply an action to a widget via the WebSocket injection bridge.

    Args:
        target: Widget selector, e.g. "@text:Open", "@name:spinBox",
                "@class:QPushButton".  Use `bv_query` first to discover
                available selectors and their "actions" list.
        action: "click" (default) or a Qt method name like "stepUp",
                "stepDown", "setText", "toggle", "setValue", etc.
                Prefer actions from the widget's "actions" array in the
                tree returned by `bv_query`.

    ⚠️  IMPORTANT — Radio buttons and checkboxes:
        Avoid `action="toggle"` on QRadioButton or QCheckBox widgets.
        `toggle()` flips internal state WITHOUT emitting signals, so
        connected slots (which update sibling widgets, validate input,
        etc.) never fire and the UI appears frozen.

        Instead, look at the PARENT WINDOW's "actions" array (the
        top-level list returned by bv_query, not the widget's own
        actions).  Use the named slot directly, e.g.:

          target="@class:VolumeToolsDlg", action="onManualACPCMode"

        This invokes the full signal-slot chain and the UI updates
        correctly.

    Returns:
        True/False string indicating whether the action succeeded.
    """
    try:
        success = act(target, action=action, port=port, timeout=timeout)
        return str(success)
    except Exception as e:
        return f"Error: {e}"


# ── Coordinate navigation ─────────────────────────────────────────────────


@mcp.tool()
def bv_coord(
    axis: str, direction: str, steps: int = 1,
    port: int = 9000, timeout: int = 10,
) -> str:
    """Move the BrainVoyager crosshair by stepping coordinate spin boxes.

    Targets the X/Y/Z coordinate spin boxes in the 3D Volume Tools dialog
    (m_XCoord, m_YCoord, m_ZCoord).  Each step moves one voxel in the
    current step size.

    Args:
        axis: "x", "y", or "z"
        direction: "up" (increase coordinate) or "down" (decrease coordinate)
        steps: Number of increments (default 1)

    Returns:
        True/False string indicating whether all steps succeeded.

    Example:
        bv_coord("x", "down", 50)   # move 50 voxels negative in X
        bv_coord("z", "up", 10)     # move 10 voxels positive in Z (rightward)
    """
    try:
        success = step_coord(axis, direction, n=steps, port=port, timeout=timeout)
        return str(success)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run()
