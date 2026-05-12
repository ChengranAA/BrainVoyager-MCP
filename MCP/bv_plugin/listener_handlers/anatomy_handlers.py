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


def _get_vmr():
    vmr = _bv.active_document
    if vmr is None:
        _bv.print_to_log("Handler: no active document.")
    return vmr


def _get_mesh_scene():
    vmr = _get_vmr()
    if vmr is None:
        return None
    return vmr.create_mesh_scene()


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
    path = _bv.create_vmr_dicom_nifti_bids(f, subj, ses, proj)
    return _ok(json.dumps({"result": path}))

def _create_vmr(data: dict) -> str:
    first = data.get("first_file", "")
    if not first:
        return _bad("Missing first_file.")
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
    doc = _bv.create_amr(
        data.get("scanner_file_type", "DICOM"), first,
        data.get("n_slices", 0), data.get("big_endian", False),
        data.get("slice_rows", 0), data.get("slice_cols", 0),
        data.get("bytes_per_pixel", 2))
    return _ok("AMR created.") if doc else _bad("Failed to create AMR.")


# ── VMR preprocessing ──────────────────────────────────────────────────────

def _vmr_deface(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps({"result": vmr.deface()}))

def _vmr_transform_to_std_sag(data: dict) -> str:
    vmr = _get_vmr()
    out = data.get("out_vmr_sag_filename", "")
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_sag_filename.")
    return _ok(json.dumps({"result": vmr.transform_to_std_sag(out)}))

def _vmr_transform_to_std_isovoxel(data: dict) -> str:
    vmr = _get_vmr()
    out = data.get("out_vmr_iso_filename", "")
    interp = data.get("interpolation_method", 1)
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    return _ok(json.dumps({"result": vmr.transform_to_std_isovoxel(interp, out)}))

def _vmr_transform_to_isovoxel(data: dict) -> str:
    vmr = _get_vmr()
    out = data.get("out_vmr_iso_filename", "")
    if vmr is None:
        return _bad("No active VMR.")
    if not out:
        return _bad("Missing out_vmr_iso_filename.")
    return _ok(json.dumps(
        {"result": vmr.transform_to_isovoxel(
            data.get("target_res", 1.0), data.get("framing_cube_dim", 256),
            data.get("interpolation_method", 1), out)}))

def _vmr_correct_intensity(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps({"result": vmr.correct_intensity_inhomogeneities()}))

def _vmr_correct_intensity_ext(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps(
        {"result": vmr.correct_intensity_inhomogeneities_ext(
            data.get("include_brain_extraction", True),
            data.get("n_cycles", 3), data.get("tissue_range_thresh", 0.25),
            data.get("intensity_thresh", 0.3),
            data.get("fit_polynom_order", 3))}))

def _vmr_normalize_to_mni(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps({"result": vmr.normalize_to_mni_space()}))

def _vmr_auto_acpc_tal(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps({"result": vmr.auto_acpc_tal_transformation()}))


# ── voxel access ───────────────────────────────────────────────────────────

def _vmr_get_voxel(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    return _ok(json.dumps(
        {"result": vmr.get_voxel_intensity(data.get("x", 0),
                                            data.get("y", 0),
                                            data.get("z", 0))}))

def _vmr_set_voxel(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    vmr.set_voxel_intensity(data.get("x", 0), data.get("y", 0),
                            data.get("z", 0), data.get("value", 0))
    return _ok("Voxel intensity set.")


# ── mesh scene ─────────────────────────────────────────────────────────────

def _mesh_create_scene(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    mesh = vmr.create_mesh_scene()
    return _ok("Mesh scene ready.") if mesh else _bad("Failed.")

def _mesh_load(data: dict) -> str:
    scene = _get_mesh_scene()
    if scene is None:
        return _bad("No mesh scene. Run mesh_create_scene first.")
    f = data.get("mesh_file", "")
    if not f:
        return _bad("Missing mesh_file.")
    _bv.print_to_log(f"MCP load mesh: {f}")
    return _ok(json.dumps({"result": scene.load_mesh(f)}))

def _mesh_add(data: dict) -> str:
    scene = _get_mesh_scene()
    if scene is None:
        return _bad("No mesh scene.")
    f = data.get("mesh_file", "")
    if not f:
        return _bad("Missing mesh_file.")
    return _ok(json.dumps({"result": scene.add_mesh(f)}))


# ── mesh morphing ──────────────────────────────────────────────────────────

def _mesh_reconstruct(_data: dict) -> str:
    scene = _get_mesh_scene()
    if scene is None:
        return _bad("No mesh scene.")
    _bv.print_to_log("MCP reconstruct mesh.")
    mesh = scene.reconstruct_mesh()
    return _ok("Mesh reconstructed.") if mesh else _bad("Reconstruction failed.")

def _mesh_smooth(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps(
        {"result": mesh.smooth_geometry(data.get("n_cycles", 20),
                                         data.get("smooth_force", 0.5))}))

def _mesh_smooth_simple(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps(
        {"result": mesh.smooth_geometry_simple(
            data.get("n_cycles", 20), data.get("smooth_force", 0.5))}))

def _mesh_inflate(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps(
        {"result": mesh.inflate_geometry(data.get("n_cycles", 100),
                                          data.get("smooth_force", 0.8))}))

def _mesh_inflate_to_sphere(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps(
        {"result": mesh.inflate_geometry_to_sphere(
            data.get("n_cycles", 300))}))

def _mesh_create_sphere(data: dict) -> str:
    scene = _get_mesh_scene()
    if scene is None:
        return _bad("No mesh scene.")
    mesh = scene.create_sphere_mesh(
        data.get("radius", 100), data.get("resol_level", 1))
    return _ok("Sphere mesh created.") if mesh else _bad("Failed.")

def _mesh_shrink_wrap(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps(
        {"result": mesh.shrink_wrap_morph(
            data.get("n_cycles", 80), data.get("find_vmr_value", 120.0))}))

def _mesh_recreate_geometry(_data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    mesh.recreate_geometry()
    return _ok("Geometry synced.")


# ── mesh save ──────────────────────────────────────────────────────────────

def _mesh_save(_data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    return _ok(json.dumps({"result": mesh.save()}))

def _mesh_save_as(data: dict) -> str:
    mesh = _get_current_mesh()
    if mesh is None:
        return _bad("No current mesh.")
    f = data.get("mesh_file", "")
    if not f:
        return _bad("Missing mesh_file.")
    remove = data.get("remove_current", False)
    return _ok(json.dumps({"result": mesh.save_as(f, remove)}))

def _mesh_update_viewer(_data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR.")
    vmr.update_viewer()
    return _ok("Viewer updated.")


def _get_current_mesh():
    scene = _get_mesh_scene()
    if scene is None:
        return None
    mesh = scene.current_mesh
    if mesh is None:
        _bv.print_to_log("Handler: no current mesh in scene.")
    return mesh


# ── MP2RAGE denoise ────────────────────────────────────────────────────────

def _mp2rage_denoise(data: dict) -> str:
    uni = data.get("path_uni")
    _bv.print_to_log(f"MCP MP2RAGE denoise: {uni}")
    try:
        output = mp2rage_genUniDen(
            chosen_factor=data.get("chosen_factor"),
            path_UNI=uni, path_INV1=data.get("path_inv1"),
            path_INV2=data.get("path_inv2"),
            uniden_filename=data.get("uniden_filename", "uniden.v16"),
            savevmr=data.get("save_vmr", True))
        if output:
            return f"HTTP/1.1 200 OK\n\n{output}"
        return _bad("Failed.")
    except Exception as e:
        _bv.print_to_log(f"MP2RAGE error: {e}")
        return _bad(f"MP2RAGE error: {e}")


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
    "vmr_create_mesh_scene":              _mesh_create_scene,
    "mesh_load":                          _mesh_load,
    "mesh_add":                           _mesh_add,
    "mesh_reconstruct":                   _mesh_reconstruct,
    "mesh_smooth":                        _mesh_smooth,
    "mesh_smooth_simple":                 _mesh_smooth_simple,
    "mesh_inflate":                       _mesh_inflate,
    "mesh_inflate_to_sphere":             _mesh_inflate_to_sphere,
    "mesh_create_sphere":                 _mesh_create_sphere,
    "mesh_shrink_wrap":                   _mesh_shrink_wrap,
    "mesh_recreate_geometry":             _mesh_recreate_geometry,
    "mesh_save":                          _mesh_save,
    "mesh_save_as":                       _mesh_save_as,
    "vmr_update_viewer":                  _mesh_update_viewer,
    "mp2rage_denoise":                    _mp2rage_denoise,
}
