# Unofficial BrainVoyager MCP — AI-controlled BrainVoyager Bridge

Control [BrainVoyager](https://www.brainvoyager.com/) from AI coding agents (Claude,
Zed, Cursor, etc.) via the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Architecture

```
┌──────────────────────┐    HTTP POST     ┌──────────────────────────────┐
│  AI Agent (Claude)   │ ──────────────→  │  bv_core_server.py           │
│                      │                  │  bv_anatomy_server.py        │
│  MCP Client config:  │                  │  bv_fmri_server.py           │
│    - BV Core         │                  │  bv_assistant_server.py      │
│    - BV Anatomy      │                  │                              │
│    - BV fMRI         │                  │  Each is a FastMCP instance  │
│    - BV Assistant    │                  │  calling _shared/bv_*        │
└──────────────────────┘                  └──────────┬───────────────────┘
                                       TCP :5050 /  │  WebSocket :9000
                                                    ▼
┌──────────────────────────────────────────────────────────────┐
│  BrainVoyager (Qt event loop)                                │
│                                                              │
│  ┌─ TCP path (document API) ─────────────────────────────┐   │
│  │  plugin/bv_plugin/mcp_listener.py ← non-blocking      │   │
│  │       │                                               │   │
│  │       │  ALL_HANDLERS["action"](data) ← O(1) dispatch │   │
│  │       ▼                                               │   │
│  │  plugin/bv_plugin/listener_handlers/                  │   │
│  │       ├── core_handlers.py    →  bv.open_document(), …│   │
│  │       ├── anatomy_handlers.py →  vmr.deface(), …      │   │
│  │       └── fmri_handlers.py    →  bv.get_vtcs_of_mdm() │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ WS path (widget introspection) ──────────────────────┐   │
│  │  bv_inject.dylib  ← DYLD_INSERT_LIBRARIES             │   │
│  │       │                                               │   │
│  │       │  Qt accessibility tree + click / invoke       │   │
│  │       ▼                                               │   │
│  │  MCP/_shared/bv_ws.py    →  query(), act()            │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  plugin/bv_auto_load/mcp_helper.py                           │
│           → MP2RAGE denoising, utilities                     │
└──────────────────────────────────────────────────────────────┘
```

**Four small servers.** This follows the MCP ecosystem
standard — the user enables only the servers they need per session, keeping the
AI's context window lean.

| Server | Tools | What it does |
|---|---|---|
| `bv_core_server` | 27 | Doc open/close/save/list, DICOM ops, log, shell, window |
| `bv_anatomy_server` | 31 | VMR pipeline, MNI/Tal, mesh morphing (reconstruct, smooth, inflate, shrink-wrap), MP2RAGE |
| `bv_fmri_server` | 22 | FMR preprocessing, VTC coregistration/creation (native/MNI/Tal), filtering, MDM |
| `bv_assistant_server` | 4 | **Experimental.** Launch BV with injection, live widget tree inspection (`bv_query`), widget interaction (`bv_act`), window discovery (`bv_list_windows`)

## Agent Skills

[Zed agent skills](https://zed.dev/docs/assistant/skills) give the AI
procedural knowledge about BrainVoyager workflows — from DICOM setup all
the way to VTC creation. Skills live in `prompts/skills/` and are loaded
on demand based on the user's request. Copy them into your Zed skills
directory to use them.

### Skill Catalog

| Skill | Covers | When to use |
|-------|--------|-------------|
| **bv-expert** | Complete BV knowledge base, User's Guide chapter finder, coordinate systems, GLM/normalization/coregistration concepts | Any BV conceptual question — "what is BBR?", "how does MNI work?" |
| **bv-dicom-setup** | DICOM rename, anonymize, series discovery, project dictionaries | "Organize my raw DICOM data" |
| **bv-anatomical-pipeline** | VMR creation, MP2RAGE denoising, IIHC, isovoxel, MNI/Talairach normalization, defacing | "Process my anatomical scan" |
| **bv-fmri-preprocessing** | FMR creation, slice timing, motion correction, HPF, spatial smoothing, EPI distortion correction (FSL topup) | "Preprocess my fMRI runs" |
| **bv-coregistration-vtc** | BBR and intensity-based coregistration, VTC creation in native/MNI/Tal space, VTC post-processing | "Coregister and create VTCs" |
| **bv-file-formats** | All BV binary formats (VMR, V16, FMR/STC, VTC, SRF, VMP, GLM, SMP, ...), axis conventions, bvbabel read/write patterns | "How do I read this VTC file?" |

### How Skills Work

Each skill's `SKILL.md` contains just a YAML frontmatter (`name` +
`description`) and concise instructions. When the user asks about a topic,
Zed matches the `description` against the request and loads the skill
automatically. The `bv-expert` skill also includes `guide-urls.md` — a
complete index of all ~190 User's Guide pages — so the agent can fetch
official documentation on demand.

### Setup

```bash
# Copy all skills into your Zed project skills directory
cp -r prompts/skills/* /path/to/project/.agents/skills/
```

Skills are auto-discovered. No restart or config change needed.

## Directory Structure

```
MCP/                            # MCP servers + shared code (run OUTSIDE BV)
├── _shared/
│   ├── bv_client.py            # call_bv() — shared by TCP-based servers
│   └── bv_ws.py                # query()/act() — WebSocket widget bridge
│
└── servers/
    ├── bv_core_server.py
    ├── bv_anatomy_server.py
    ├── bv_fmri_server.py
    └── bv_assistant_server.py  # EXPERIMENTAL — widget introspection

plugin/                         # Everything that runs INSIDE BrainVoyager
├── bv_ui_control/              # DYLD injection dylib (C++) + Python client
│   ├── src/                    #   → C++ WebSocket server injected into BV
│   ├── bv.py                   #   → Python client for the injection bridge
│   └── CMakeLists.txt
│
├── bv_plugin/                  # → Run inside BV's Python Development Panel
│   ├── mcp_listener.py         #   Run this from BV's Python Plugin editor
│   └── listener_handlers/      #   Hash-table dispatch (no if/elif chains)
│       ├── core_handlers.py
│       ├── anatomy_handlers.py
│       └── fmri_handlers.py
│
└── bv_auto_load/               # → Copy into BV's Python Scripts directory
    └── mcp_helper.py           #   MP2RAGE denoising, VMR utilities
```

## Quick Start

### 1. Inside BrainVoyager

Copy the files inside of `plugin/bv_auto_load/` into BrainVoyager's `PythonScripts` folder. Then open BV's **Python Development** panel, open `plugin/bv_plugin/mcp_listener.py`, and
run it. You should see:

```
SUCCESS: Real-time listener active on 127.0.0.1:5050
```

BV's UI stays responsive thanks to a non-blocking socket polled by QTimer.

### 2. MCP Client Config
Set up python environment with uv using `uv sync`.

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

### 3. (Optional) BV UI Assistant — WebSocket injection bridge

The assistant server lets an AI agent **see and interact with BV's UI widgets**
in real time (click buttons, query the widget tree, invoke Qt methods).
It uses `bv_inject.dylib`, which must be loaded into BV at launch:

```bash
DYLD_INSERT_LIBRARIES=/path/to/bv_mcp/plugin/bv_ui_control/build/src/libbv_inject.dylib \
    /Applications/BrainVoyager.app/Contents/MacOS/BrainVoyager
```

Add this server to your MCP config if you want UI automation:

```json
"BrainVoyager Assistant": {
  "command": "uv",
  "args": [
    "run",
    "--directory",
    "/path/to/bv_mcp",
    "python",
    "MCP/servers/bv_assistant_server.py"
  ]
}
```

**Selectors.** Widgets are addressed with a `@type:value` syntax:

| Selector | Matches | Example |
|---|---|---|
| `@text:Open` | Any widget whose visible text contains "Open" | Click the Open button |
| `@name:spinBox` | Widget with Qt `objectName="spinBox"` | `bv_act("@name:spinBox", "stepUp")` |
| `@class:QPushButton` | Any widget of that Qt class | Find all buttons |

**Workflow:** `bv_query` → scan the widget tree → `bv_act` with selector.

Replace `/path/to/bv_mcp` with the actual path to this project.  Enable only
the servers you need — disable the rest to keep the AI's context small.

### 4. Verify

Ask your AI agent: *"List the BrainVoyager methods available."*

---

## Adding a New BV API Command

1. Add a handler in `plugin/bv_plugin/listener_handlers/<domain>_handlers.py`:
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
