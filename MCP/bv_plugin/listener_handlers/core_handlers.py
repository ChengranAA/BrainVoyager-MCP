"""Core action handlers — document, DICOM, log, UI, shell.

Each handler receives the parsed JSON *data* dict and returns a complete HTTP
response string (``STATUS\n\nBODY``).  They are dispatched by the listener's
``ALL_HANDLERS`` hash table — zero branching, O(1) lookup.
"""

import json


# ── helpers ────────────────────────────────────────────────────────────────


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"


def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── general commands ───────────────────────────────────────────────────────


def _methods(_data: dict) -> str:
    bv.print_to_log("MCP requested method list.")
    return _ok(json.dumps({"result": list(bv.methods())}))


def _describe_method(data: dict) -> str:
    name = data.get("method_name", "")
    bv.print_to_log(f"MCP requested description of method: {name}")
    doc = bv.describe_method(name)
    return _ok(json.dumps({"result": doc}))


def _close_all(_data: dict) -> str:
    bv.print_to_log("MCP instructed to close all documents.")
    bv.close_all()
    return _ok("All documents closed.")


# ── document open ──────────────────────────────────────────────────────────


def _open_document(data: dict) -> str:
    path = data.get("path", "")
    bv.print_to_log(f"MCP instructed to open: {path}")
    doc = bv.open_document(path)
    if doc is not None:
        return _ok("Document opened successfully.")
    return _bad("BrainVoyager rejected the file format.")


def _open_advanced(data: dict) -> str:
    path = data.get("path", "")
    close_current = data.get("close_current_doc", False)
    remove_current = data.get("remove_current_doc", False)
    bv.print_to_log(
        f"MCP instructed to open (close_current={close_current}, "
        f"remove_current={remove_current}): {path}"
    )
    doc = bv.open(path, close_current_doc=close_current, remove_current_doc=remove_current)
    if doc is not None:
        return _ok("Document opened successfully.")
    return _bad("BrainVoyager rejected the file format.")


def _get_doc_attributes(_data: dict) -> str:
    doc = bv.active_document
    if doc is None:
        return _bad("No active document.")
    bv.print_to_log("MCP requested document attributes.")
    info = (
        f"Document: {doc.file_name}, "
        f"Dimensions: {doc.dim_x}x{doc.dim_y}x{doc.dim_z}, "
        f"Voxel Size: {doc.voxelsize_x}, {doc.voxelsize_y}, {doc.voxelsize_z}, "
        f"Volumes: {doc.n_volumes} (TR: {doc.TR}ms), "
        f"Path: {doc.path_file_name}"
    )
    return _ok(json.dumps({"result": info}))


# ── DICOM ──────────────────────────────────────────────────────────────────


def _rename_dicoms(data: dict) -> str:
    path = data.get("path", "")
    bv.print_to_log(f"MCP instructed to rename DICOMs in: {path}")
    bv.rename_dicoms(path)
    return _ok("DICOM renaming process initiated.")


def _anonymize_dicoms(data: dict) -> str:
    path = data.get("path")
    patient_name = data.get("patient_name", "")
    if not path or not patient_name:
        return _bad("Missing path or patient_name.")
    bv.print_to_log(f"MCP instructed to anonymize DICOMs in: {path} as '{patient_name}'")
    bv.anonymize_dicoms(path, patient_name)
    return _ok("DICOM anonymization process initiated.")


def _deface_anat_dicoms(data: dict) -> str:
    in_dir = data.get("input_directory")
    out_dir = data.get("output_directory")
    if not in_dir or not out_dir:
        return _bad("Missing input_directory or output_directory.")
    bv.print_to_log(f"MCP instructed to deface DICOMs: {in_dir} -> {out_dir}")
    result = bv.deface_anat_dicoms(in_dir, out_dir)
    return _ok(json.dumps({"result": result}))


# ── log pane ───────────────────────────────────────────────────────────────


def _show_log_pane(_data: dict) -> str:
    bv.show_log_pane()
    return _ok("Log pane shown.")


def _hide_log_pane(_data: dict) -> str:
    bv.hide_log_pane()
    return _ok("Log pane hidden.")


def _print_to_log(data: dict) -> str:
    text = data.get("text", "")
    bv.print_to_log(text)
    return _ok("Text printed to log.")


# ── shell ──────────────────────────────────────────────────────────────────


def _run_cmd(data: dict) -> str:
    cmd = data.get("shell_command", "")
    bv.print_to_log(f"MCP instructed to run shell command: {cmd}")
    output = bv.run_cmd(cmd)
    return _ok(json.dumps({"result": output}))


# ── application control ────────────────────────────────────────────────────


def _exit(_data: dict) -> str:
    bv.print_to_log("MCP instructed BrainVoyager to exit.")
    bv.exit()
    return _ok("Exiting BrainVoyager.")


# ── dialogs ────────────────────────────────────────────────────────────────


def _show_message_box(data: dict) -> str:
    message = data.get("message", "")
    bv.show_message_box(message)
    return _ok("Message box shown.")


def _show_timeout_message_box(data: dict) -> str:
    message = data.get("message", "")
    duration = data.get("duration", 3000)
    result = bv.show_timeout_message_box(message, duration)
    return _ok(json.dumps({"result": result}))


# ── window control ─────────────────────────────────────────────────────────


def _move_window(data: dict) -> str:
    nx = data.get("new_x", 0)
    ny = data.get("new_y", 0)
    bv.move_window(nx, ny)
    return _ok("Window moved.")


def _resize_window(data: dict) -> str:
    w = data.get("new_width", 800)
    h = data.get("new_height", 600)
    bv.resize_window(w, h)
    return _ok("Window resized.")


# ── file / directory choosers ──────────────────────────────────────────────


def _choose_directory(data: dict) -> str:
    instruction = data.get("instruction", "Select a directory")
    chosen = bv.choose_directory(instruction)
    return _ok(json.dumps({"result": chosen}))


def _choose_file(data: dict) -> str:
    instruction = data.get("instruction", "Select a file")
    filter_str = data.get("filter", "*")
    chosen = bv.choose_file(instruction, filter_str)
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
