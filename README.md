# Unofficial BrainVoyager MCP — BrainVoyager MCP Bridge

A bridge that lets AI coding agents (like Claude, Zed, etc.) control
[BrainVoyager](https://www.brainvoyager.com/) via the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

A very not smart implementation...

## What it does

This project exposes BrainVoyager's automation API as MCP tools, so an AI agent can
directly drive BV workflows: load/create anatomical/functional datasets, run
preprocessing pipelines (inhomogeneity correction, iso-voxel resampling, MNI
normalization, defacing, Talairach transformation), manage DICOM files, and query
document attributes — all through natural language instructions.

Two components work together:

- **`mcp_server.py`** — the MCP server (FastMCP). This is what the AI agent talks to.
  Each BV API call is wrapped as an `@mcp.tool()`, and the server forwards requests
  to the listener running inside BrainVoyager.
- **`mcp_listener.py`** — a TCP listener that runs *inside* BrainVoyager's Python
  plugin environment. It receives commands on `127.0.0.1:5050` and executes them
  against the live BV instance.

## The trick: getting BrainVoyager to spawn a server

BrainVoyager has a built-in Python plugin system, but you can't start a long-running
server process from within it — BV's main thread would block and the UI would freeze.

The workaround is to use **Qt's event loop**:

1. Create a **non-blocking** TCP socket (call `setblocking(False)` on the socket).
2. Use `QTimer` (from PyQt5, PySide2, or PySide6 — BV ships with one of them) to
   poll that socket on a recurring interval (e.g. every 100 ms).
3. Paste the entire `mcp_listener.py` script into BV's **Python plugin editor** and
   run it. The timer-driven polling integrates cleanly with Qt's event loop, so BV
   stays responsive while continuously listening for commands.

In short: **non-blocking socket + QTimer = a server that doesn't freeze
BrainVoyager.**

## Quick start

1. Start BrainVoyager.
2. Open the Python plugin panel, paste `mcp_listener.py`, and run it.
3. Config the MCP server in your favorite MCP client. 
```{json}
{
  /// Configure an MCP server that runs locally via stdin/stdout
  ///
  /// The name of your MCP server
  "BrainVoyager": {
    /// The command which runs the MCP server
    "command": "/opt/homebrew/Caskroom/miniconda/base/envs/mcp/bin/python",
    /// The arguments to pass to the MCP server
    "args": ["/Users/chengran/Documents/small_projects/bv_mcp/MCP/mcp_server.py"],
    /// The environment variables to set
    "env": {}
  }
}
```
4. Point your MCP client at the server. The agent can now control BV.
