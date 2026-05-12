"""fMRI action handlers — FMR creation, preprocessing, VTC, MDM.

``_bv`` is injected by ``listener_handlers.set_bv()`` at listener startup.
"""

import json

# Injected by set_bv() — do NOT use bare `bv` as an implicit global.
_bv = None


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"

def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── FMR creation ───────────────────────────────────────────────────────────

def _create_fmr_dicom(data: dict) -> str:
    f = data.get("file_of_series", "")
    stc = data.get("fmr_stc_filename", "")
    tf = data.get("target_folder", "")
    pf = data.get("protocol_file", "")
    if not f or not stc or not tf:
        return _bad("Missing file_of_series, fmr_stc_filename, or target_folder.")
    _bv.print_to_log(f"MCP create FMR from DICOM: {f} → {tf}/{stc}")
    doc = _bv.create_fmr_dicom(f, stc, tf, pf)
    return _ok("FMR created.") if doc else _bad("Failed to create FMR.")


def _create_fmr_dicom_nifti_bids(data: dict) -> str:
    f = data.get("file_of_series", "")
    subj = data.get("subj_id", 1)
    ses = data.get("ses_id", 1)
    run = data.get("run_id", 1)
    task = data.get("task_name", "")
    proj = data.get("project_folder", "")
    pf = data.get("protocol_file", "")
    if not f or not task or not proj:
        return _bad("Missing file_of_series, task_name, or project_folder.")
    _bv.print_to_log(
        f"MCP FMR NIfTI BIDS: {f} subj={subj} ses={ses} "
        f"run={run} task={task} → {proj}")
    path = _bv.create_fmr_dicom_nifti_bids(f, subj, ses, run, task, proj, pf)
    return _ok(json.dumps({"result": path}))


# ── FMR preprocessing ──────────────────────────────────────────────────────

def _fmr_correct_motion(_data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    _bv.print_to_log("MCP FMR motion correction.")
    return _ok(json.dumps({"result": fmr.correct_motion()}))


def _fmr_correct_motion_to_vol(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    target = data.get("target_vol_idx", 0)
    _bv.print_to_log(f"MCP FMR motion correction to vol {target}.")
    return _ok(json.dumps({"result": fmr.correct_motion_to_vol(target)}))


def _fmr_correct_slicetiming(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    interp = data.get("interpolation_method", 1)
    _bv.print_to_log(f"MCP FMR slice timing correction (interp={interp}).")
    return _ok(json.dumps(
        {"result": fmr.correct_slicetiming_using_timingtable(interp)}))


def _fmr_smooth_spatial(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    fwhm = data.get("gauss_fwhm", 4.0)
    unit = data.get("fwhm_unit", "mm")
    _bv.print_to_log(f"MCP FMR spatial smooth: {fwhm} {unit}.")
    return _ok(json.dumps({"result": fmr.smooth_spatial(fwhm, unit)}))


def _fmr_smooth_temporal(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    fwhm = data.get("gauss_fwhm", 2.0)
    unit = data.get("fwhm_unit", "data_points")
    _bv.print_to_log(f"MCP FMR temporal smooth: {fwhm} {unit}.")
    return _ok(json.dumps({"result": fmr.smooth_temporal(fwhm, unit)}))


def _fmr_filter_highpass_fourier(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    n = data.get("n_cycles", 3)
    _bv.print_to_log(f"MCP FMR high-pass (Fourier, {n} cycles).")
    return _ok(json.dumps(
        {"result": fmr.filter_temporal_highpass_glm_fourier(n)}))


def _fmr_filter_highpass_dct(data: dict) -> str:
    fmr = _bv.active_document
    if fmr is None:
        return _bad("No active FMR document.")
    n = data.get("n_basis_functions", 2)
    _bv.print_to_log(f"MCP FMR high-pass (DCT, {n} bases).")
    return _ok(json.dumps(
        {"result": fmr.filter_temporal_highpass_glm_dct(n)}))


# ── MDM / VTC ──────────────────────────────────────────────────────────────

def _get_vtcs_of_mdm(data: dict) -> str:
    mdm = data.get("mdm_file", "")
    if not mdm:
        return _bad("Missing mdm_file.")
    vtcs = _bv.get_vtcs_of_mdm(mdm)
    return _ok(json.dumps({"result": list(vtcs)}))


# ── dispatch table ─────────────────────────────────────────────────────────

HANDLERS: dict[str, callable] = {
    "create_fmr_dicom":              _create_fmr_dicom,
    "create_fmr_dicom_nifti_bids":   _create_fmr_dicom_nifti_bids,
    "fmr_correct_motion":            _fmr_correct_motion,
    "fmr_correct_motion_to_vol":     _fmr_correct_motion_to_vol,
    "fmr_correct_slicetiming":       _fmr_correct_slicetiming,
    "fmr_smooth_spatial":            _fmr_smooth_spatial,
    "fmr_smooth_temporal":           _fmr_smooth_temporal,
    "fmr_filter_highpass_fourier":   _fmr_filter_highpass_fourier,
    "fmr_filter_highpass_dct":       _fmr_filter_highpass_dct,
    "get_vtcs_of_mdm":               _get_vtcs_of_mdm,
}
