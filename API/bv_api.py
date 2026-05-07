"""
bv_api.py — BrainVoyager Python API abstraction layer.

Thin, typed, synchronous wrapper around the BrainVoyager Qt listener
(http://127.0.0.1:5050).  All functions communicate with the listener
via HTTP POST, just as mcp_server.py does, but return native Python
types and raise exceptions on errors instead of returning formatted
strings.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BV_LISTENER_URL: str = "http://127.0.0.1:5050"
"""Base URL of the BrainVoyager Qt listener."""

DEFAULT_TIMEOUT: int = 30
"""Default HTTP request timeout in seconds.  Override per-call via *_ex() helpers."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BVError(Exception):
    """Raised when BrainVoyager returns an error (e.g. bad action, missing file)."""


class BVConnectionError(Exception):
    """Raised when the Qt listener is unreachable (BrainVoyager not running / listener not started)."""


class BVFileNotFoundError(BVError):
    """Raised when a required file or directory does not exist on disk."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_result(response: requests.Response) -> Any:
    """Extract the ``result`` key from the listener's JSON response body."""
    try:
        data = json.loads(response.text)
        return data.get("result", response.text)
    except (json.JSONDecodeError, ValueError):
        return response.text


def _post(action: str, payload: dict[str, Any] | None = None, *, timeout: int | None = None) -> requests.Response:
    """Send a JSON POST to the listener.  Return the raw ``Response`` on 200; raise otherwise."""
    if payload is None:
        payload = {}
    payload["action"] = action
    t = timeout if timeout is not None else DEFAULT_TIMEOUT
    try:
        resp = requests.post(BV_LISTENER_URL, json=payload, timeout=t)
    except requests.exceptions.ConnectionError:
        raise BVConnectionError(
            "Connection Error: Is the Qt listener running in BrainVoyager?"
        ) from None
    if resp.status_code != 200:
        raise BVError(f"BrainVoyager returned HTTP {resp.status_code}: {resp.text}")
    return resp


def _resolve_path(path: str) -> str:
    """Expand ``~`` and validate existence.  Returns the resolved absolute path."""
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        raise BVFileNotFoundError(f"File not found: '{expanded}'")
    return expanded


def _resolve_dir(path: str) -> str:
    """Expand ``~`` and validate it is a directory."""
    expanded = os.path.expanduser(path)
    if not os.path.isdir(expanded):
        raise BVFileNotFoundError(f"Directory not found: '{expanded}'")
    return expanded


def _resolve_file(path: str) -> str:
    """Expand ``~`` and validate it is a regular file."""
    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        raise BVFileNotFoundError(f"File not found: '{expanded}'")
    return expanded


# ===================================================================
# Public API — General Commands
# ===================================================================

def get_bv_methods() -> list[str]:
    """Return a list of all method names supported by the BrainVoyager object."""
    resp = _post("methods")
    result = _parse_result(resp)
    if isinstance(result, list):
        return result
    # result might be a string representation of a list
    return list(result) if hasattr(result, "__iter__") else [str(result)]


def describe_bv_method(method_name: str) -> str:
    """Return the docstring for *method_name* on the BrainVoyager object."""
    resp = _post("describe_method", {"method_name": method_name})
    return str(_parse_result(resp))


def close_all_bv_documents() -> None:
    """Close all open documents in BrainVoyager's multi-document workspace."""
    _post("close_all")


def get_bv_document_attributes() -> str:
    """Return attributes of the currently active VMR/FMR/DMR/NIfTI document."""
    resp = _post("get_doc_attributes", timeout=15)
    return str(_parse_result(resp))


# ===================================================================
# Public API — Document Open Commands
# ===================================================================

def open_bv_document(file_path: str) -> None:
    """Open *file_path* (.vmr, .fmr, .dmr, or NIfTI) in BrainVoyager."""
    _post("open_document", {"path": _resolve_path(file_path)})


def open_bv_document_advanced(
    file_path: str,
    close_current_doc: bool = False,
    remove_current_doc: bool = False,
) -> None:
    """Open *file_path* with options to close or remove the current document."""
    _post("open", {
        "path": _resolve_path(file_path),
        "close_current_doc": close_current_doc,
        "remove_current_doc": remove_current_doc,
    })


# ===================================================================
# Public API — Document Creation Commands
# ===================================================================

def create_vmr_from_bv_dicom(file_of_series: str) -> None:
    """Create a VMR from one DICOM file of a 3D anatomical series."""
    _post("create_vmr_dicom", {"file_of_series": _resolve_path(file_of_series)}, timeout=30)


def create_vmr_nifti_bids_from_bv_dicom(
    file_of_series: str,
    subj_id: int,
    ses_id: int,
    project_folder: str,
) -> str | None:
    """
    Create a BIDS-compliant NIfTI from DICOM data.

    Returns the path to the created NIfTI file, or ``None`` on failure.
    """
    payload = {
        "file_of_series": _resolve_path(file_of_series),
        "subj_id": subj_id,
        "ses_id": ses_id,
        "project_folder": project_folder,
    }
    resp = _post("create_vmr_dicom_nifti_bids", payload, timeout=60)
    result = _parse_result(resp)
    return result if result else None


def create_vmr_from_bv_raw(
    first_file: str,
    n_slices: int,
    scanner_file_type: str = "DICOM",
    big_endian: bool = False,
    slice_rows: int = 0,
    slice_cols: int = 0,
    bytes_per_pixel: int = 2,
) -> None:
    """Create a VMR document from raw MRI files with full parameter control."""
    _post("create_vmr", {
        "scanner_file_type": scanner_file_type,
        "first_file": _resolve_path(first_file),
        "n_slices": n_slices,
        "big_endian": big_endian,
        "slice_rows": slice_rows,
        "slice_cols": slice_cols,
        "bytes_per_pixel": bytes_per_pixel,
    }, timeout=30)


def create_amr_from_bv_raw(
    first_file: str,
    n_slices: int,
    scanner_file_type: str = "DICOM",
    big_endian: bool = False,
    slice_rows: int = 0,
    slice_cols: int = 0,
    bytes_per_pixel: int = 2,
) -> None:
    """Create an AMR document from raw MRI files."""
    _post("create_amr", {
        "scanner_file_type": scanner_file_type,
        "first_file": _resolve_path(first_file),
        "n_slices": n_slices,
        "big_endian": big_endian,
        "slice_rows": slice_rows,
        "slice_cols": slice_cols,
        "bytes_per_pixel": bytes_per_pixel,
    }, timeout=30)


# ===================================================================
# Public API — VMR Document Methods
# ===================================================================

def deface_bv_vmr() -> bool:
    """
    Deface the active VMR (1 mm iso-voxel required).

    Returns ``True`` on success.
    """
    resp = _post("vmr_deface", timeout=60)
    return bool(_parse_result(resp))


def transform_bv_vmr_to_std_sag(out_vmr_sag_filename: str) -> bool:
    """
    Reorient the active VMR to standard sagittal (radiological).

    Returns ``True`` on success, ``False`` if already sagittal.
    """
    resp = _post("vmr_transform_to_std_sag", {"out_vmr_sag_filename": out_vmr_sag_filename}, timeout=60)
    return bool(_parse_result(resp))


def transform_bv_vmr_to_std_isovoxel(
    out_vmr_iso_filename: str,
    interpolation_method: int = 1,
) -> bool:
    """
    Resample the active VMR to 1.0 mm iso-voxel in a 256³ framing cube.

    *interpolation_method*: 1 = trilinear, 2 = cubic spline, 3 = sinc.

    Returns ``True`` on success, ``False`` if already 1 mm iso-voxel.
    """
    resp = _post("vmr_transform_to_std_isovoxel", {
        "out_vmr_iso_filename": out_vmr_iso_filename,
        "interpolation_method": interpolation_method,
    }, timeout=120)
    return bool(_parse_result(resp))


def transform_bv_vmr_to_isovoxel(
    out_vmr_iso_filename: str,
    target_res: float = 1.0,
    framing_cube_dim: int = 256,
    interpolation_method: int = 1,
) -> bool:
    """
    Resample the active VMR to a custom iso-voxel resolution.

    *interpolation_method*: 1 = trilinear, 2 = cubic spline, 3 = sinc.

    Returns ``True`` on success.
    """
    resp = _post("vmr_transform_to_isovoxel", {
        "out_vmr_iso_filename": out_vmr_iso_filename,
        "target_res": target_res,
        "framing_cube_dim": framing_cube_dim,
        "interpolation_method": interpolation_method,
    }, timeout=120)
    return bool(_parse_result(resp))


def correct_bv_vmr_intensity_inhomogeneities() -> bool:
    """
    Correct IIH of the active VMR (3 cycles, defaults, brain extraction).

    Saves ``[name]_IIHC.vmr`` and ``[name]_BrainMask.vmr``.
    The active VMR holds corrected data afterwards.

    Returns ``True`` on success.
    """
    resp = _post("vmr_correct_intensity_inhomogeneities", timeout=300)
    return bool(_parse_result(resp))


def correct_bv_vmr_intensity_inhomogeneities_ext(
    include_brain_extraction: bool = True,
    n_cycles: int = 3,
    tissue_range_thresh: float = 0.25,
    intensity_thresh: float = 0.3,
    fit_polynom_order: int = 3,
) -> bool:
    """
    Correct IIH with full parameter control.

    Returns ``True`` on success.
    """
    resp = _post("vmr_correct_intensity_inhomogeneities_ext", {
        "include_brain_extraction": include_brain_extraction,
        "n_cycles": n_cycles,
        "tissue_range_thresh": tissue_range_thresh,
        "intensity_thresh": intensity_thresh,
        "fit_polynom_order": fit_polynom_order,
    }, timeout=600)
    return bool(_parse_result(resp))


def normalize_bv_vmr_to_mni_space() -> bool:
    """
    Normalize the active VMR to MNI-152 space.

    Requires brain-extracted, IIH-corrected data.
    Saves MNI VMR + TRF files; closes native VMR & loads MNI.

    Returns ``True`` on success.
    """
    resp = _post("vmr_normalize_to_mni_space", timeout=300)
    return bool(_parse_result(resp))


def auto_acpc_tal_bv_vmr_transformation() -> bool:
    """
    Perform automatic ACPC + Talairach transformation on the active VMR.

    Requires brain-extracted, IIH-corrected data.
    Saves ACPC/TAL VMRs, TAL file, TRF files.

    Returns ``True`` on success.
    """
    resp = _post("vmr_auto_acpc_tal_transformation", timeout=300)
    return bool(_parse_result(resp))


def get_bv_vmr_voxel_intensity(x: int, y: int, z: int) -> int:
    """
    Return the intensity value (0–225) at voxel *(x, y, z)* in the active VMR.

    .. note:: Slow for iterating over all voxels.
    """
    resp = _post("vmr_get_voxel_intensity", {"x": x, "y": y, "z": z}, timeout=10)
    return int(_parse_result(resp))


def set_bv_vmr_voxel_intensity(x: int, y: int, z: int, value: int) -> None:
    """
    Set the intensity at voxel *(x, y, z)* to *value* (0–225).

    .. note:: Slow for iterating over all voxels.
    """
    _post("vmr_set_voxel_intensity", {"x": x, "y": y, "z": z, "value": value}, timeout=10)


def create_bv_vmr_mesh_scene() -> None:
    """Create (or retrieve) a MeshScene for the active VMR."""
    _post("vmr_create_mesh_scene", timeout=10)


def update_bv_vmr_viewer() -> None:
    """Update the 3D Viewer (OpenGL) attached to the active VMR."""
    _post("vmr_update_viewer", timeout=10)


# ===================================================================
# Public API — DICOM Commands
# ===================================================================

def rename_bv_dicoms(directory: str) -> None:
    """
    Rename raw DICOM files in *directory* to:
    ``PatientsName-SeriesNumber-VolumeNumber-ImageNumber.dcm``
    """
    _post("rename_dicoms", {"path": _resolve_dir(directory)}, timeout=15)


def anonymize_bv_dicoms(directory: str, anonymized_patient_name: str) -> None:
    """
    Rename DICOMs to standard format and replace the patient name.

    Files renamed to:
    ``PatientsName-SeriesNumber-VolumeNumber-ImageNumber.dcm``
    """
    _post("anonymize_dicoms", {
        "path": _resolve_dir(directory),
        "patient_name": anonymized_patient_name,
    }, timeout=30)


def deface_bv_anatomical_dicoms(input_directory: str, output_directory: str) -> bool:
    """
    Deface anatomical DICOMs (3D, 1 mm iso voxels required).

    Normalizes to MNI, applies defacing mask in native space,
    saves ``defaced_*`` copies into *output_directory*.

    Returns ``True`` on success.
    """
    payload = {
        "input_directory": _resolve_dir(input_directory),
        "output_directory": os.path.expanduser(output_directory),
    }
    resp = _post("deface_anat_dicoms", payload, timeout=120)
    return bool(_parse_result(resp))


# ===================================================================
# Public API — Log Pane Commands
# ===================================================================

def show_bv_log_pane() -> None:
    """Show the BrainVoyager Log pane."""
    _post("show_log_pane")


def hide_bv_log_pane() -> None:
    """Hide the BrainVoyager Log pane."""
    _post("hide_log_pane")


def print_to_bv_log(text: str) -> None:
    """Print *text* (simple HTML allowed) to the BrainVoyager Log pane."""
    _post("print_to_log", {"text": text})


# ===================================================================
# Public API — Shell Command
# ===================================================================

def run_bv_shell_command(shell_command: str) -> str:
    """
    Execute *shell_command* via BrainVoyager and return stdout.

    .. warning:: BrainVoyager blocks until the command completes.
    """
    resp = _post("run_cmd", {"shell_command": shell_command}, timeout=30)
    return str(_parse_result(resp))


# ===================================================================
# Public API — Application Control
# ===================================================================

def exit_bv() -> None:
    """Quit BrainVoyager.  Use with caution."""
    _post("exit")


# ===================================================================
# Public API — Dialog / Message Commands
# ===================================================================

def show_bv_message_box(message: str) -> None:
    """Show a message-box dialog in BrainVoyager."""
    _post("show_message_box", {"message": message})


def show_bv_timeout_message_box(message: str, duration: int = 3000) -> str:
    """
    Show a message box that auto-closes after *duration* ms.

    Returns the user's response string (e.g. ``"OK"``, ``"Cancel"``).
    """
    resp = _post("show_timeout_message_box", {"message": message, "duration": duration})
    return str(_parse_result(resp))


# ===================================================================
# Public API — Window Control
# ===================================================================

def move_bv_window(new_x: int, new_y: int) -> None:
    """Move the BrainVoyager main window to (*new_x*, *new_y*)."""
    _post("move_window", {"new_x": new_x, "new_y": new_y})


def resize_bv_window(new_width: int, new_height: int) -> None:
    """Resize the BrainVoyager main window to *new_width* × *new_height*."""
    _post("resize_window", {"new_width": new_width, "new_height": new_height})


# ===================================================================
# Public API — File / Directory Choosers
# ===================================================================

def choose_bv_directory(instruction: str = "Select a directory") -> str:
    """
    Open a directory-chooser dialog in BrainVoyager.

    Returns the selected path, or an empty ``str`` if cancelled.
    """
    resp = _post("choose_directory", {"instruction": instruction}, timeout=60)
    return str(_parse_result(resp))


def choose_bv_file(instruction: str = "Select a file", filter: str = "*") -> str:
    """
    Open a file-chooser dialog in BrainVoyager.

    *filter*: e.g. ``"*.vmr"``.

    Returns the selected path, or an empty ``str`` if cancelled.
    """
    resp = _post("choose_file", {"instruction": instruction, "filter": filter}, timeout=60)
    return str(_parse_result(resp))


# ===================================================================
# Public API — MDM / VTCs
# ===================================================================

def get_vtcs_of_mdm(mdm_file: str) -> list[str]:
    """Return VTC file paths referenced in an ``.mdm`` file."""
    resp = _post("get_vtcs_of_mdm", {"mdm_file": _resolve_file(mdm_file)}, timeout=10)
    result = _parse_result(resp)
    if isinstance(result, list):
        return result
    return list(result) if hasattr(result, "__iter__") else [str(result)]
