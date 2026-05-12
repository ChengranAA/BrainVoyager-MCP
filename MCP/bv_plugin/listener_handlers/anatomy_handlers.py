"""Anatomy action handlers — VMR creation, pipeline, mesh, MP2RAGE.

Dispatched by hash table from the listener.  Each function receives the parsed
JSON body and returns a complete ``STATUS\\n\\nBODY`` HTTP response string.
"""

import json

from mcp_helper import mp2rage_genUniDen


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"


def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── document creation ──────────────────────────────────────────────────────

def _create_vmr_dicom(data: dict) -> str:
    file_of_series = data.get("file_of_series", "")
    if not file_of_series:
        return _bad("Missing file_of_series.")
    bv.print_to_log(f"MCP instructed to create VMR from DICOM: {file_of_series}")
    doc = bv.create_vmr_dicom(file_of_series)
    if doc is not None:
        return _ok("VMR document created successfully.")
    return _bad("Failed to create VMR document.")


def _create_vmr_dicom_nifti_bids(data: dict) -> str:
    f = data.get("file_of_series", "")
    subj = data.get("subj_id", 1)
    ses = data.get("ses_id", 1)
    proj = data.get("project_folder", "")
    if not f or not proj:
        return _bad("Missing file_of_series or project_folder.")
    bv.print_to_log(
        f"MCP instructed to create VMR NIfTI BIDS: {f} "
        f"subj={subj} ses={ses} project={proj}"
    )
    nifti_path = bv.create_vmr_dicom_nifti_bids(f, subj, ses, proj)
    return _ok(json.dumps({"result": nifti_path}))


def _create_vmr(data: dict) -> str:
    first = data.get("first_file", "")
    if not first:
        return _bad("Missing first_file.")
    bv.print_to_log(
        f"MCP instructed to create VMR: type={data.get('scanner_file_type', 'DICOM')} "
        f"file={first}"
    )
    doc = bv.create_vmr(
        data.get("scanner_file_type", "DICOM"),
        first,
        data.get("n_slices", 0),
        data.get("big_endian", False),
        data.get("slice_rows", 0),
        data.get("slice_cols", 0),
        data.get("bytes_per_pixel", 2),
    )
    if doc is not None:
        return _ok("VMR document created successfully.")
    return _bad("Failed to create VMR document.")


def _create_amr(data: dict) -> str:
    first = data.get("first_file", "")
    if not first:
        return _bad("Missing first_file.")
    bv.print_to_log(
        f"MCP instructed to create AMR: type={data.get('scanner_file_type', 'DICOM')} "
        f"file={first}"
    )
    doc = bv.create_amr(
        data.get("scanner_file_type", "DICOM"),
        first,
        data.get("n_slices", 0),
        data.get("big_endian", False),
        data.get("slice_rows", 0),
        data.get("slice_cols", 0),
        data.get("bytes_per_pixel", 2),
    )
    if doc is not None:
        return _ok("AMR document created successfully.")
    return _bad("Failed to create AMR document.")


# ── VMR preprocessing ──────────────────────────────────────────────────────


def _vmr_deface(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log("MCP instructed to deface active VMR.")
    result = vmr.deface()
    return _ok(json.dumps({"result": result}))


def _vmr_transform_to_std_sag(data: dict) -> str:
    vmr = bv.active_document
    out = data.get("out_vmr_sag_filename", "")
    if vmr is None:
        return _bad("No active VMR document.")
    if not out:
        return _bad("Missing out_vmr_sag_filename.")
    bv.print_to_log(f"MCP instructed to transform VMR to std sag: {out}")
    result = vmr.transform_to_std_sag(out)
    return _ok(json.dumps({"result": result}))


def _vmr_transform_to_std_isovoxel(data: dict) -> str:
    vmr = bv.active_document
    out = data.get("out_vmr_iso_filename", "")
    interp = data.get("interpolation_method", 1)
    if vmr is None:
        return _bad("No active VMR document.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    bv.print_to_log(f"MCP instructed to transform VMR to std isovoxel (1mm): {out}")
    result = vmr.transform_to_std_isovoxel(interp, out)
    return _ok(json.dumps({"result": result}))


def _vmr_transform_to_isovoxel(data: dict) -> str:
    vmr = bv.active_document
    out = data.get("out_vmr_iso_filename", "")
    if vmr is None:
        return _bad("No active VMR document.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    res = data.get("target_res", 1.0)
    cube = data.get("framing_cube_dim", 256)
    interp = data.get("interpolation_method", 1)
    bv.print_to_log(
        f"MCP instructed to transform VMR to isovoxel "
        f"(res={res}, cube={cube}): {out}"
    )
    result = vmr.transform_to_isovoxel(res, cube, interp, out)
    return _ok(json.dumps({"result": result}))


def _vmr_correct_intensity(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log("MCP instructed to correct intensity inhomogeneities.")
    result = vmr.correct_intensity_inhomogeneities()
    return _ok(json.dumps({"result": result}))


def _vmr_correct_intensity_ext(data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log(
        f"MCP instructed to correct intensity inhomogeneities (ext): "
        f"cycles={data.get('n_cycles', 3)}, "
        f"brain_extr={data.get('include_brain_extraction', True)}"
    )
    result = vmr.correct_intensity_inhomogeneities_ext(
        data.get("include_brain_extraction", True),
        data.get("n_cycles", 3),
        data.get("tissue_range_thresh", 0.25),
        data.get("intensity_thresh", 0.3),
        data.get("fit_polynom_order", 3),
    )
    return _ok(json.dumps({"result": result}))


def _vmr_normalize_to_mni(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log("MCP instructed to normalize VMR to MNI space.")
    result = vmr.normalize_to_mni_space()
    return _ok(json.dumps({"result": result}))


def _vmr_auto_acpc_tal(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log("MCP instructed to perform auto ACPC/Talairach transformation.")
    result = vmr.auto_acpc_tal_transformation()
    return _ok(json.dumps({"result": result}))


# ── voxel access ───────────────────────────────────────────────────────────


def _vmr_get_voxel(data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    x, y, z = data.get("x", 0), data.get("y", 0), data.get("z", 0)
    bv.print_to_log(f"MCP requested voxel intensity at ({x}, {y}, {z}).")
    return _ok(json.dumps({"result": vmr.get_voxel_intensity(x, y, z)}))


def _vmr_set_voxel(data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    x, y, z = data.get("x", 0), data.get("y", 0), data.get("z", 0)
    val = data.get("value", 0)
    bv.print_to_log(f"MCP instructed to set voxel ({x}, {y}, {z}) to {val}.")
    vmr.set_voxel_intensity(x, y, z, val)
    return _ok("Voxel intensity set.")


# ── mesh / viewer ──────────────────────────────────────────────────────────


def _vmr_create_mesh_scene(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    bv.print_to_log("MCP instructed to create mesh scene for VMR.")
    mesh_scene = vmr.create_mesh_scene()
    if mesh_scene is not None:
        return _ok("Mesh scene created/retrieved successfully.")
    return _bad("Failed to create mesh scene.")


def _vmr_update_viewer(_data: dict) -> str:
    vmr = bv.active_document
    if vmr is None:
        return _bad("No active VMR document.")
    vmr.update_viewer()
    return _ok("VMR viewer updated.")


# ── MP2RAGE denoise ────────────────────────────────────────────────────────


def _mp2rage_denoise(data: dict) -> str:
    chosen = data.get("chosen_factor")
    uni = data.get("path_uni")
    inv1 = data.get("path_inv1")
    inv2 = data.get("path_inv2")
    fname = data.get("uniden_filename", "uniden.v16")
    save_vmr = data.get("save_vmr", True)

    bv.print_to_log(f"MCP instructed to run MP2RAGE denoise on: {uni}")

    try:
        output = mp2rage_genUniDen(
            chosen_factor=chosen,
            path_UNI=uni,
            path_INV1=inv1,
            path_INV2=inv2,
            uniden_filename=fname,
            savevmr=save_vmr,
        )
        if output:
            return f"HTTP/1.1 200 OK\n\n{output}"
        return _bad("Failed to return an output path.")
    except Exception as e:
        bv.print_to_log(f"Error during MP2RAGE denoise: {e}")
        return _bad(f"Error processing MP2RAGE denoise: {e}")


# ── dispatch table ─────────────────────────────────────────────────────────

HANDLERS: dict[str, callable] = {
    "create_vmr_dicom":                   _create_vmr_dicom,
    "create_vmr_dicom_nifti_bids":        _create_vmr_dicom_nifti_bids,
    "create_vmr":                         _create_vmr,
    "create_amr":                         _create_amr,
    "vmr_deface":                         _vmr_deface,
    "vmr_transform_to_std_sag":           _vmr_transform_to_std_sag,
    "vmr_transform_to_std_isovoxel":      _vmr_transform_to_std_isovoxel,
    "vmr_transform_to_isovoxel":          _vmr_transform_to_isovoxel,
    "vmr_correct_intensity_inhomogeneities":      _vmr_correct_intensity,
    "vmr_correct_intensity_inhomogeneities_ext":  _vmr_correct_intensity_ext,
    "vmr_normalize_to_mni_space":         _vmr_normalize_to_mni,
    "vmr_auto_acpc_tal_transformation":   _vmr_auto_acpc_tal,
    "vmr_get_voxel_intensity":            _vmr_get_voxel,
    "vmr_set_voxel_intensity":            _vmr_set_voxel,
    "vmr_create_mesh_scene":              _vmr_create_mesh_scene,
    "vmr_update_viewer":                  _vmr_update_viewer,
    "mp2rage_denoise":                    _mp2rage_denoise,
}
