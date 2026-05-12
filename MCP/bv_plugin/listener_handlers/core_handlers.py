"""Core action handlers — document, DICOM, log, UI, shell.

``_bv`` is injected by ``listener_handlers.set_bv()`` at listener startup.
"""

import json

# Injected by set_bv() — do NOT use bare `bv` as an implicit global.
_bv = None


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"

def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── general commands ───────────────────────────────────────────────────────

def _methods(_data: dict) -> str:
    _bv.print_to_log("MCP requested method list.")
    return _ok(json.dumps({"result": list(_bv.methods())}))

def _describe_method(data: dict) -> str:
    name = data.get("method_name", "")
    _bv.print_to_log(f"MCP requested description of method: {name}")
    return _ok(json.dumps({"result": _bv.describe_method(name)}))

def _close_all(_data: dict) -> str:
    _bv.print_to_log("MCP instructed to close all documents.")
    _bv.close_all()
    return _ok("All documents closed.")


# ── document open ──────────────────────────────────────────────────────────

def _open_document(data: dict) -> str:
    path = data.get("path", "")
    _bv.print_to_log(f"MCP instructed to open: {path}")
    doc = _bv.open_document(path)
    return _ok("Document opened.") if doc else _bad("BV rejected the format.")

def _open_advanced(data: dict) -> str:
    path = data.get("path", "")
    close = data.get("close_current_doc", False)
    remove = data.get("remove_current_doc", False)
    _bv.print_to_log(f"MCP open (close={close}, remove={remove}): {path}")
    doc = _bv.open(path, close_current_doc=close, remove_current_doc=remove)
    return _ok("Document opened.") if doc else _bad("BV rejected the format.")

def _get_doc_attributes(_data: dict) -> str:
    doc = _bv.active_document
    if doc is None:
        return _bad("No active document.")
    _bv.print_to_log("MCP requested document attributes.")
    info = (
        f"Document: {doc.file_name}, "
        f"Dimensions: {doc.dim_x}x{doc.dim_y}x{doc.dim_z}, "
        f"Voxel: {doc.voxelsize_x}, {doc.voxelsize_y}, {doc.voxelsize_z}, "
        f"Volumes: {doc.n_volumes} (TR: {doc.TR}ms), "
        f"Path: {doc.path_file_name}"
    )
    return _ok(json.dumps({"result": info}))


# ── DICOM ──────────────────────────────────────────────────────────────────

def _rename_dicoms(data: dict) -> str:
    path = data.get("path", "")
    _bv.print_to_log(f"MCP rename DICOMs in: {path}")
    _bv.rename_dicoms(path)
    return _ok("DICOM renaming initiated.")

def _anonymize_dicoms(data: dict) -> str:
    path = data.get("path")
    name = data.get("patient_name", "")
    if not path or not name:
        return _bad("Missing path or patient_name.")
    _bv.print_to_log(f"MCP anonymize DICOMs: {path} as '{name}'")
    _bv.anonymize_dicoms(path, name)
    return _ok("DICOM anonymization initiated.")

def _deface_anat_dicoms(data: dict) -> str:
    in_dir = data.get("input_directory")
    out_dir = data.get("output_directory")
    if not in_dir or not out_dir:
        return _bad("Missing input_directory or output_directory.")
    _bv.print_to_log(f"MCP deface DICOMs: {in_dir} -> {out_dir}")
    result = _bv.deface_anat_dicoms(in_dir, out_dir)
    return _ok(json.dumps({"result": result}))


# ── log pane ───────────────────────────────────────────────────────────────

def _show_log_pane(_data: dict) -> str:
    _bv.show_log_pane()
    return _ok("Log pane shown.")

def _hide_log_pane(_data: dict) -> str:
    _bv.hide_log_pane()
    return _ok("Log pane hidden.")

def _print_to_log(data: dict) -> str:
    _bv.print_to_log(data.get("text", ""))
    return _ok("Text printed to log.")


# ── shell ──────────────────────────────────────────────────────────────────

def _run_cmd(data: dict) -> str:
    cmd = data.get("shell_command", "")
    _bv.print_to_log(f"MCP shell: {cmd}")
    return _ok(json.dumps({"result": _bv.run_cmd(cmd)}))


# ── application control ────────────────────────────────────────────────────

def _exit(_data: dict) -> str:
    _bv.print_to_log("MCP exit.")
    _bv.exit()
    return _ok("Exiting BrainVoyager.")


# ── dialogs ────────────────────────────────────────────────────────────────

def _show_message_box(data: dict) -> str:
    _bv.show_message_box(data.get("message", ""))
    return _ok("Message box shown.")

def _show_timeout_message_box(data: dict) -> str:
    result = _bv.show_timeout_message_box(
        data.get("message", ""), data.get("duration", 3000))
    return _ok(json.dumps({"result": result}))


# ── window control ─────────────────────────────────────────────────────────

def _move_window(data: dict) -> str:
    _bv.move_window(data.get("new_x", 0), data.get("new_y", 0))
    return _ok("Window moved.")

def _resize_window(data: dict) -> str:
    _bv.resize_window(data.get("new_width", 800), data.get("new_height", 600))
    return _ok("Window resized.")


# ── file / directory choosers ──────────────────────────────────────────────

def _choose_directory(data: dict) -> str:
    chosen = _bv.choose_directory(data.get("instruction", "Select a directory"))
    return _ok(json.dumps({"result": chosen}))

def _choose_file(data: dict) -> str:
    chosen = _bv.choose_file(
        data.get("instruction", "Select a file"),
        data.get("filter", "*"))
    return _ok(json.dumps({"result": chosen}))


# ── dispatch table ─────────────────────────────────────────────────────────

HANDLERS: dict[str, callable] = {
    "methods":                   _methods,
    "describe_method":           _describe_method,
    "close_all":                 _close_all,
    "open_document":             _open_document,
    "open":                      _open_advanced,
    "get_doc_attributes":        _get_doc_attributes,
    "rename_dicoms":             _rename_dicoms,
    "anonymize_dicoms":          _anonymize_dicoms,
    "deface_anat_dicoms":        _deface_anat_dicoms,
    "show_log_pane":             _show_log_pane,
    "hide_log_pane":             _hide_log_pane,
    "print_to_log":              _print_to_log,
    "run_cmd":                   _run_cmd,
    "exit":                      _exit,
    "show_message_box":          _show_message_box,
    "show_timeout_message_box":  _show_timeout_message_box,
    "move_window":               _move_window,
    "resize_window":             _resize_window,
    "choose_directory":          _choose_directory,
    "choose_file":               _choose_file,
}
