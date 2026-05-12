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


# ── helpers ────────────────────────────────────────────────────────────────

def _get_vmr():
    """Return active VMR or None, logging appropriately."""
    vmr = _bv.active_document
    if vmr is None:
        _bv.print_to_log("VTC handler: no active document.")
    return vmr

def _get_fmr():
    """Return active FMR or None."""
    fmr = _bv.active_document
    if fmr is None:
        _bv.print_to_log("FMR handler: no active document.")
    return fmr


# ── FMR creation ───────────────────────────────────────────────────────────

def _create_fmr_dicom(data: dict) -> str:
    f = data.get("file_of_series", "")
    stc = data.get("fmr_stc_filename", "")
    tf = data.get("target_folder", "")
    pf = data.get("protocol_file", "")
    if not f or not stc or not tf:
        return _bad("Missing file_of_series, fmr_stc_filename, or target_folder.")
    _bv.print_to_log(f"MCP create FMR from DICOM: {f}")
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
    path = _bv.create_fmr_dicom_nifti_bids(f, subj, ses, run, task, proj, pf)
    return _ok(json.dumps({"result": path}))


# ── FMR preprocessing ──────────────────────────────────────────────────────

def _fmr_correct_motion(_data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    _bv.print_to_log("MCP FMR motion correction.")
    return _ok(json.dumps({"result": fmr.correct_motion()}))


def _fmr_correct_motion_to_vol(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    target = data.get("target_vol_idx", 0)
    return _ok(json.dumps({"result": fmr.correct_motion_to_vol(target)}))


def _fmr_correct_slicetiming(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    interp = data.get("interpolation_method", 1)
    return _ok(json.dumps(
        {"result": fmr.correct_slicetiming_using_timingtable(interp)}))


def _fmr_smooth_spatial(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    return _ok(json.dumps(
        {"result": fmr.smooth_spatial(data.get("gauss_fwhm", 4.0),
                                       data.get("fwhm_unit", "mm"))}))


def _fmr_smooth_temporal(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    return _ok(json.dumps(
        {"result": fmr.smooth_temporal(data.get("gauss_fwhm", 2.0),
                                        data.get("fwhm_unit", "data_points"))}))


def _fmr_filter_highpass_fourier(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    n = data.get("n_cycles", 3)
    return _ok(json.dumps(
        {"result": fmr.filter_temporal_highpass_glm_fourier(n)}))


def _fmr_filter_highpass_dct(data: dict) -> str:
    fmr = _get_fmr()
    if fmr is None:
        return _bad("No active FMR document.")
    n = data.get("n_basis_functions", 2)
    return _ok(json.dumps(
        {"result": fmr.filter_temporal_highpass_glm_dct(n)}))


# ── VTC — coregistration & creation ────────────────────────────────────────

def _vtc_link(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    f = data.get("vtc_file", "")
    if not f:
        return _bad("Missing vtc_file.")
    _bv.print_to_log(f"MCP link VTC: {f}")
    return _ok(json.dumps({"result": vmr.link_vtc(f)}))


def _vtc_save(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    f = data.get("vtc_file", "")
    if not f:
        return _bad("Missing vtc_file.")
    return _ok(json.dumps({"result": vmr.save_vtc(f)}))


def _vtc_coregister_fmr(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    fmr = data.get("fmr_file", "")
    if not fmr:
        return _bad("Missing fmr_file.")
    _bv.print_to_log(f"MCP coregister FMR->VMR: {fmr}")
    result = vmr.coregister_fmr_to_vmr(
        fmr, data.get("iihc_func", False),
        data.get("use_attached_amr", 0))
    return _ok(json.dumps({"result": result}))


def _vtc_coregister_fmr_bbr(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    fmr = data.get("fmr_file", "")
    if not fmr:
        return _bad("Missing fmr_file.")
    _bv.print_to_log(f"MCP coregister FMR->VMR (BBR): {fmr}")
    return _ok(json.dumps(
        {"result": vmr.coregister_fmr_to_vmr_using_bbr(fmr)}))


def _vtc_create_native(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    _bv.print_to_log("MCP create VTC in native space.")
    return _ok(json.dumps(
        {"result": vmr.create_vtc_in_native_space(
            data.get("fmr_file"), data.get("coreg_ia_trf_file"),
            data.get("coreg_fa_trf_file"), data.get("vtc_file"),
            data.get("res_to_anat", 1), data.get("interpolation_method", 1),
            data.get("bounding_box_intensity_threshold", 100),
            data.get("data_type", 2))}))


def _vtc_create_mni(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    _bv.print_to_log("MCP create VTC in MNI space.")
    return _ok(json.dumps(
        {"result": vmr.create_vtc_in_mni_space(
            data.get("fmr_file"), data.get("coreg_ia_trf_file"),
            data.get("coreg_fa_trf_file"), data.get("mni_trf_file"),
            data.get("vtc_file"), data.get("res_to_anat", 1),
            data.get("interpolation_method", 1),
            data.get("bounding_box_intensity_threshold", 100),
            data.get("data_type", 2))}))


def _vtc_create_tal(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    _bv.print_to_log("MCP create VTC in Talairach space.")
    return _ok(json.dumps(
        {"result": vmr.create_vtc_in_tal_space(
            data.get("fmr_file"), data.get("coreg_ia_trf_file"),
            data.get("coreg_fa_trf_file"), data.get("acpc_trf_file"),
            data.get("tal_file"), data.get("vtc_file"),
            data.get("res_to_anat", 1), data.get("interpolation_method", 1),
            data.get("bounding_box_intensity_threshold", 100),
            data.get("data_type", 2))}))


# ── VTC preprocessing ──────────────────────────────────────────────────────

def _vtc_smooth_spatial(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    return _ok(json.dumps(
        {"result": vmr.smooth_spatial(data.get("gauss_fwhm", 4.0),
                                       data.get("fwhm_unit", "mm"))}))


def _vtc_smooth_temporal(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    return _ok(json.dumps(
        {"result": vmr.smooth_temporal(data.get("gauss_fwhm", 2.0),
                                        data.get("fwhm_unit", "data_points"))}))


def _vtc_filter_highpass_fourier(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    return _ok(json.dumps(
        {"result": vmr.filter_temporal_highpass_glm_fourier(
            data.get("n_cycles", 3))}))


def _vtc_filter_highpass_dct(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    return _ok(json.dumps(
        {"result": vmr.filter_temporal_highpass_glm_dct(
            data.get("n_basis_functions", 2))}))


def _vtc_filter_highpass_fft(data: dict) -> str:
    vmr = _get_vmr()
    if vmr is None:
        return _bad("No active VMR document.")
    return _ok(json.dumps(
        {"result": vmr.filter_temporal_highpass_fft(
            data.get("highpass", 0.008), data.get("highpass_unit", "Hz"))}))


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
    "vtc_link":                      _vtc_link,
    "vtc_save":                      _vtc_save,
    "vtc_coregister_fmr":            _vtc_coregister_fmr,
    "vtc_coregister_fmr_bbr":        _vtc_coregister_fmr_bbr,
    "vtc_create_native":             _vtc_create_native,
    "vtc_create_mni":                _vtc_create_mni,
    "vtc_create_tal":                _vtc_create_tal,
    "vtc_smooth_spatial":            _vtc_smooth_spatial,
    "vtc_smooth_temporal":           _vtc_smooth_temporal,
    "vtc_filter_highpass_fourier":   _vtc_filter_highpass_fourier,
    "vtc_filter_highpass_dct":       _vtc_filter_highpass_dct,
    "vtc_filter_highpass_fft":       _vtc_filter_highpass_fft,
    "get_vtcs_of_mdm":               _get_vtcs_of_mdm,
}
