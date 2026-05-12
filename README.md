# Unofficial BrainVoyager MCP — AI-controlled BrainVoyager Bridge

Control [BrainVoyager](https://www.brainvoyager.com/) from AI coding agents (Claude,
Zed, Cursor, etc.) via the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Architecture

```
┌──────────────────────┐    HTTP POST     ┌──────────────────────────────┐
│  AI Agent (Claude)   │ ──────────────→  │  bv_core_server.py           │
│                      │                  │  bv_anatomy_server.py         │
│  MCP Client config:  │                  │  bv_fmri_server.py            │
│    - BV Core         │                  │                              │
│    - BV Anatomy      │                  │  Each is a FastMCP instance  │
│    - BV fMRI         │                  │  calling _shared/bv_client   │
└──────────────────────┘                  └──────────┬───────────────────┘
                                                     │ TCP :5050
                                                     ▼
┌──────────────────────────────────────────────────────────────┐
│  BrainVoyager (Qt event loop)                                │
│                                                              │
│  bv_plugin/mcp_listener.py  ← non-blocking TCP + QTimer      │
│       │                                                      │
│       │  ALL_HANDLERS["action"](data)   ← O(1) hash table    │
│       ▼                                                      │
│  bv_plugin/listener_handlers/                                │
│       ├── core_handlers.py    →  bv.open_document(), etc.     │
│       ├── anatomy_handlers.py →  vmr.deface(), etc.          │
│       └── fmri_handlers.py    →  bv.get_vtcs_of_mdm(), etc.   │
│                                                              │
│  bv_auto_load/mcp_helper.py  →  MP2RAGE denoising, utilities │
└──────────────────────────────────────────────────────────────┘
```

**Three small servers instead of one monolith.** This follows the MCP ecosystem
standard — the user enables only the servers they need per session, keeping the
AI's context window lean.

| Server | Tools | What it does |
|---|---|---|
| `bv_core_server` | 27 | Doc open/close/save/list, DICOM ops, log, shell, window |
| `bv_anatomy_server` | 31 | VMR pipeline, MNI/Tal, mesh morphing (reconstruct, smooth, inflate, shrink-wrap), MP2RAGE |
| `bv_fmri_server` | 22 | FMR preprocessing, VTC coregistration/creation (native/MNI/Tal), filtering, MDM |

## Directory Structure

```
MCP/
├── _shared/
│   └── bv_client.py            # call_bv() — shared by all 3 MCP servers
│
├── servers/                    # MCP server entry points (run OUTSIDE BV)
│   ├── bv_core_server.py
│   ├── bv_anatomy_server.py
│   └── bv_fmri_server.py
│
├── bv_plugin/                  # → Copy into BV's plugin directory
│   ├── mcp_listener.py         # Run this from BV's Python Plugin editor
│   └── listener_handlers/      # Hash-table dispatch (no if/elif chains)
│       ├── core_handlers.py
│       ├── anatomy_handlers.py
│       └── fmri_handlers.py
│
└── bv_auto_load/               # → Copy into BV's auto-load directory
    └── mcp_helper.py           # MP2RAGE denoising, VMR utilities
```

## Quick Start

### 1. Inside BrainVoyager

Copy the `bv_auto_load/` and `bv_plugin/` folders into BrainVoyager's plugin
directory. Then open BV's **Python Plugin** panel, open `mcp_listener.py`, and
run it. You should see:

```
SUCCESS: Real-time listener active on 127.0.0.1:5050
```

BV's UI stays responsive thanks to a non-blocking socket polled by QTimer.

### 2. MCP Client Config

Uses `uv run` to pick up the project's Python environment automatically:

```json
{
  "mcpServers": {
    "BrainVoyager Core": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/bv_mcp",
        "python",
        "MCP/servers/bv_core_server.py"
      ]
    },
    "BrainVoyager Anatomy": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/bv_mcp",
        "python",
        "MCP/servers/bv_anatomy_server.py"
      ]
    },
    "BrainVoyager fMRI": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/bv_mcp",
        "python",
        "MCP/servers/bv_fmri_server.py"
      ]
    }
  }
}
```

Replace `/path/to/bv_mcp` with the actual path to this project.  Enable only
the servers you need — disable the rest to keep the AI's context small.

### 3. Verify

Ask your AI agent: *"List the BrainVoyager methods available."*

---

## Adding a New BV API Command

1. Add a handler in `bv_plugin/listener_handlers/<domain>_handlers.py`:
   ```python
   def _vmr_new_command(data: dict) -> str:
       vmr = _bv.active_document
       result = vmr.new_command(data.get("param", "default"))
       return _ok(json.dumps({"result": result}))
   ```
2. Register it in the `HANDLERS` dict at the bottom of the same file:
   ```python
   HANDLERS = {
       # ...
       "vmr_new_command": _vmr_new_command,  # ← one line
   }
   ```
3. Add the MCP tool in `servers/<domain>_server.py`:
   ```python
   @mcp.tool()
   def new_vmr_command(param: str = "default") -> str:
       """Docstring..."""
       return call_bv("vmr_new_command", timeout=30, param=param)
   ```

No changes needed in `mcp_listener.py`. The dispatch table picks it up automatically.
