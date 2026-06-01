# bv_ui_control

DYLD injection library + Python client for BrainVoyager UI widget automation.

## Inspiration

This project was inspired by [**qt-widgeteer**](https://github.com/AurynRobotics/qt-widgeteer),
an excellent Qt6 UI testing and automation framework designed for LLM agent
control.  qt-widgeteer provides a full-featured WebSocket server with
recording, event broadcasting, wait conditions, screenshots, and dozens of
commands.

`bv_ui_control` takes the same idea but strips it down to the essential four
commands needed by the BrainVoyager MCP bridge:

| Command | What it does |
|---|---|
| `list_windows` | Enumerate all top-level Qt windows |
| `get_tree` | Walk the widget tree to a given depth |
| `click` | Click a widget by `@text` / `@name` / `@class` selector |
| `invoke` | Invoke a Qt slot or `Q_INVOKABLE` method on a widget |

Everything is implemented in a single C++ file (`src/mylib.cpp`) with **no
external dependencies beyond Qt6**.  No third-party libraries, no submodules.

## How It Works

```
┌────────────────────────────┐
│  BrainVoyager (Qt app)     │
│                            │
│  bv_inject.dylib injected  │  ← DYLD_INSERT_LIBRARIES
│  via ObjC method swizzling │
│                            │
│  ┌──────────────────────┐  │
│  │  BVInjectServer      │  │  WebSocket on ws://localhost:9000
│  │  (QWebSocketServer)  │◄─┼──────── JSON commands ──────┐
│  └──────────────────────┘  │                            │
└────────────────────────────┘                ┌──────────────────────┐
                                              │  Python client       │
                                              │  (bv.py / bv_ws.py) │
                                              └──────────────────────┘
```

## Building

```bash
cd plugin/bv_ui_control
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

Requires: CMake 3.18+, Qt 6.8+ (matches BrainVoyager's bundled Qt), C++17.

## Usage

### 1. Inject into BrainVoyager

```bash
DYLD_INSERT_LIBRARIES=./build/src/libbv_inject.dylib \
    /Applications/BrainVoyager.app/Contents/MacOS/BrainVoyager
```

BV's log will show:
```
[bv_ui_control] Injected — WebSocket server on port 9000
[bv_ui_control] Connect via:  ws://localhost:9000
```

### 2. Control from Python

```python
import bv

# See what's on screen
info = bv.query()
print(info["title"])            # 'BrainVoyager'
print(info["tree"]["children"]) # top-level widgets

# Click a button
bv.act("@text:Open")

# Spin a coordinate
bv.act("@name:m_ZCoordMiniTools", "stepUp")
```

### 3. Use with the MCP bridge

The library at `MCP/_shared/bv_ws.py` uses the same protocol.  Enable the
`bv_assistant_server` in your MCP config to let AI agents query and interact
with BV's UI in real time.

## Differences from qt-widgeteer

| Feature | qt-widgeteer | bv_ui_control |
|---|---|---|
| Commands | 30+ | 4 |
| Screenshots | ✓ | — |
| Recording & replay | ✓ | — |
| Event broadcasting | ✓ | — |
| Wait conditions | ✓ | — |
| External dependencies | 0 (Qt only) | 0 (Qt only) |
| Code size | ~4,000 lines | ~370 lines |
| Build dependency | Static lib | Single dylib |

`bv_ui_control` intentionally does less.  It targets one specific use case
(AI agents controlling BrainVoyager via MCP) and keeps the implementation
simple enough to audit in one sitting.

## License

MIT — same as qt-widgeteer.
