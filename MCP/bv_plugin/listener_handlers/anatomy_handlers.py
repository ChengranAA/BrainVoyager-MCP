"""Anatomy action handlers — VMR creation, pipeline, mesh, MP2RAGE.

``_bv`` is injected by ``listener_handlers.set_bv()`` at listener startup.
"""

import json
from mcp_helper import mp2rage_genUniDen

# Injected by set_bv() — do NOT use bare `bv` as an implicit global.
_bv = None


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"

def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── document creation ──────────────────────────────────────────────────────

def _create_vmr_dicom(data: dict) -> str:
    f = data.get("file_of_series", "")
    if not f:
        return _bad("Missing file_of_series.")
    _bv.print_to_log(f"MCP create VMR from DICOM: {f}")
    doc = _bv.create_vmr_dicom(f)
    return _ok("VMR created.") if doc else _bad("Failed to create VMR.")

def _create_vmr_dicom_nifti_bids(data: dict) -> str:
    f = data.get("file_of_series", "")
    subj = data.get("subj_id", 1)
    ses = data.get("ses_id", 1)
    proj = data.get("project_folder", "")
    if not f or not proj:
        return _bad("Missing file_of_series or project_folder.")
    _bv.print_to_log(f"MCP VMR NIfTI BIDS: {f} subj={subj} ses={ses} proj={proj}")
    path = _bv.create_vmr_dicom_nifti_bids(f, subj, ses, proj)
    return _ok(json.dumps({"result": path}))

def _create_vmr(data: dict) -> str:
    first = data.get("first_file", "")
    if not first:
        return _bad("Missing first_file.")
    _bv.print_to_log(f"MCP create VMR: {data.get('scanner_file_type', 'DICOM')} {first}")
    doc = _bv.create_vmr(
        data.get("scanner_file_type", "DICOM"), first,
        data.get("n_slices", 0), data.get("big_endian", False),
        data.get("slice_rows", 0), data.get("slice_cols", 0),
        data.get("bytes_per_pixel", 2))
    return _ok("VMR created.") if doc else _bad("Failed to create VMR.")

def _create_amr(data: dict) -> str:
    first = data.get("first_file", "")
    if not first:
        return _bad("Missing first_file.")
    _bv.print_to_log(f"MCP create AMR: {data.get('scanner_file_type', 'DICOM')} {first}")
    doc = _bv.create_amr(
        data.get("scanner_file_type", "DICOM"), first,
        data.get("n_slices", 0), data.get("big_endian", False),
        data.get("slice_rows", 0), data.get("slice_cols", 0),
        data.get("bytes_per_pixel", 2))
    return _ok("AMR created.") if doc else _bad("Failed to create AMR.")


# ── VMR preprocessing ──────────────────────────────────────────────────────

def _vmr_deface(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log("MCP deface VMR.")
    return _ok(json.dumps({"result": vmr.deface()}))

def _vmr_transform_to_std_sag(data: dict) -> str:
    vmr = _bv.active_document
    out = data.get("out_vmr_sag_filename", "")
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_sag_filename.")
    _bv.print_to_log(f"MCP VMR → std sag: {out}")
    return _ok(json.dumps({"result": vmr.transform_to_std_sag(out)}))

def _vmr_transform_to_std_isovoxel(data: dict) -> str:
    vmr = _bv.active_document
    out = data.get("out_vmr_iso_filename", "")
    interp = data.get("interpolation_method", 1)
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    _bv.print_to_log(f"MCP VMR → std isovoxel: {out}")
    return _ok(json.dumps({"result": vmr.transform_to_std_isovoxel(interp, out)}))

def _vmr_transform_to_isovoxel(data: dict) -> str:
    vmr = _bv.active_document
    out = data.get("out_vmr_iso_filename", "")
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    res = data.get("target_res", 1.0)
    cube = data.get("framing_cube_dim", 256)
    interp = data.get("interpolation_method", 1)
    _bv.print_to_log(f"MCP VMR → isovoxel (res={res}, cube={cube}): {out}")
    return _ok(json.dumps({"result": vmr.transform_to_isovoxel(res, cube, interp, out)}))

def _vmr_correct_intensity(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log("MCP IIHC.")
    return _ok(json.dumps({"result": vmr.correct_intensity_inhomogeneities()}))

def _vmr_correct_intensity_ext(data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log(f"MCP IIHC ext: cycles={data.get('n_cycles', 3)}")
    result = vmr.correct_intensity_inhomogeneities_ext(
        data.get("include_brain_extraction", True),
        data.get("n_cycles", 3),
        data.get("tissue_range_thresh", 0.25),
        data.get("intensity_thresh", 0.3),
        data.get("fit_polynom_order", 3))
    return _ok(json.dumps({"result": result}))

def _vmr_normalize_to_mni(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log("MCP normalize to MNI.")
    return _ok(json.dumps({"result": vmr.normalize_to_mni_space()}))

def _vmr_auto_acpc_tal(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log("MCP ACPC/Talairach.")
    return _ok(json.dumps({"result": vmr.auto_acpc_tal_transformation()}))


# ── voxel access ───────────────────────────────────────────────────────────

def _vmr_get_voxel(data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    x, y, z = data.get("x", 0), data.get("y", 0), data.get("z", 0)
    return _ok(json.dumps({"result": vmr.get_voxel_intensity(x, y, z)}))

def _vmr_set_voxel(data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    vmr.set_voxel_intensity(data.get("x", 0), data.get("y", 0),
                            data.get("z", 0), data.get("value", 0))
    return _ok("Voxel intensity set.")


# ── mesh / viewer ──────────────────────────────────────────────────────────

def _vmr_create_mesh_scene(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    _bv.print_to_log("MCP create mesh scene.")
    mesh = vmr.create_mesh_scene()
    return _ok("Mesh scene ready.") if mesh else _bad("Failed.")

def _vmr_update_viewer(_data: dict) -> str:
    vmr = _bv.active_document
    if vmr is None:
        return _bad("No active VMR.")
    vmr.update_viewer()
    return _ok("VMR viewer updated.")


# ── MP2RAGE denoise ────────────────────────────────────────────────────────

def _mp2rage_denoise(data: dict) -> str:
    uni = data.get("path_uni")
    _bv.print_to_log(f"MCP MP2RAGE denoise: {uni}")
    try:
        output = mp2rage_genUniDen(
            chosen_factor=data.get("chosen_factor"),
            path_UNI=uni,
            path_INV1=data.get("path_inv1"),
            path_INV2=data.get("path_inv2"),
            uniden_filename=data.get("uniden_filename", "uniden.v16"),
            savevmr=data.get("save_vmr", True))
        if output:
            return f"HTTP/1.1 200 OK\n\n{output}"
        return _bad("Failed to return output path.")
    except Exception as e:
        _bv.print_to_log(f"MP2RAGE error: {e}")
        return _bad(f"MP2RAGE denoise error: {e}")


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
