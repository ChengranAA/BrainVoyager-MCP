import os
import json
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BrainVoyager Bridge Server")
BV_LISTENER_URL = "http://127.0.0.1:5050"


def _parse_bv_result(response) -> str:
    """
    Try to parse a JSON result from the listener response.
    Falls back to returning the raw text if parsing fails.
    """
    try:
        data = json.loads(response.text)
        return str(data.get("result", response.text))
    except (json.JSONDecodeError, ValueError):
        return response.text

@mcp.tool()
def open_bv_document(file_path: str) -> str:
    """
    Opens a document in BrainVoyager. Supports .vmr, .fmr, .dmr, and NIfTI.
    """
    expanded_path = os.path.expanduser(file_path)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "open_document", "path": expanded_path},
            timeout=5
        )
        if response.status_code == 200:
            return f"Success: Instructed BrainVoyager to open '{expanded_path}'."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"

@mcp.tool()
def rename_bv_dicoms(directory: str) -> str:
    """
    Renames raw DICOM files in a folder to a standard BrainVoyager format:
    PatientsName-SeriesNumber-VolumeNumber-ImageNumber.dcm

    Args:
        directory: The absolute or relative path to the folder containing DICOM files.
    """
    expanded_dir = os.path.expanduser(directory)
    if not os.path.isdir(expanded_dir):
        return f"Error: Directory not found at '{expanded_dir}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            # Note the action is now "rename_dicoms"
            json={"action": "rename_dicoms", "path": expanded_dir},
            timeout=15 # Increased timeout because renaming multiple files takes longer
        )
        if response.status_code == 200:
            return f"Success: BrainVoyager is renaming DICOMs in '{expanded_dir}'."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"

# ---------------------------------------------------------------------------
# General Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def get_bv_methods() -> str:
    """
    Returns a list of all methods supported by the BrainVoyager object.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "methods"},
            timeout=5
        )
        if response.status_code == 200:
            return f"BrainVoyager methods:\n{_parse_bv_result(response)}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def describe_bv_method(method_name: str) -> str:
    """
    Returns documentation for the specified BrainVoyager method.

    Args:
        method_name: Name of the BrainVoyager method to describe.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "describe_method", "method_name": method_name},
            timeout=5
        )
        if response.status_code == 200:
            return _parse_bv_result(response)
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def close_all_bv_documents() -> str:
    """
    Closes all open documents in the BrainVoyager multi-document workspace.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "close_all"},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: All documents closed in BrainVoyager."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def get_bv_document_attributes() -> str:
    """
    Get the current active document and returns all its attributes at once.
    Works for VMR, FMR, DMR, and NIfTI files.

    Returns dimension, voxel/pixel sizes, slice info, TR, volumes,
    file paths, preprocessing names, mesh scene status, and more.

    Args:
        file_path: Path to the document to inspect.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "get_doc_attributes"},
            timeout=15
        )
        if response.status_code == 200:
            attrs = _parse_bv_result(response)
            return attrs
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Document Open Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def open_bv_document_advanced(
    file_path: str,
    close_current_doc: bool = False,
    remove_current_doc: bool = False
) -> str:
    """
    Opens a document in BrainVoyager with options to close/remove the current doc.
    Supports .vmr, .fmr, .dmr, and NIfTI.

    Args:
        file_path: Path to the document to open.
        close_current_doc: If True, close the currently active document first.
        remove_current_doc: If True, remove the current document's files from disk.
    """
    expanded_path = os.path.expanduser(file_path)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "open",
                "path": expanded_path,
                "close_current_doc": close_current_doc,
                "remove_current_doc": remove_current_doc
            },
            timeout=5
        )
        if response.status_code == 200:
            return f"Success: Instructed BrainVoyager to open '{expanded_path}'."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Document Creation Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def create_vmr_from_bv_dicom(file_of_series: str) -> str:
    """
    Creates a VMR document from a DICOM file of an anatomical 3D series.
    Only needs one file of the series; all parameters are extracted from
    the DICOM header.

    Args:
        file_of_series: Path to one DICOM file of the anatomical series.
    """
    expanded_path = os.path.expanduser(file_of_series)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "create_vmr_dicom", "file_of_series": expanded_path},
            timeout=30
        )
        if response.status_code == 200:
            return "Success: VMR document created from DICOM."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def create_vmr_nifti_bids_from_bv_dicom(
    file_of_series: str,
    subj_id: int,
    ses_id: int,
    project_folder: str
) -> str:
    """
    Creates a BIDS-compliant NIfTI file from DICOM anatomical data.
    Saves the NIfTI and sidecar JSON into a BIDS project folder.

    Args:
        file_of_series: Path to one DICOM file of the anatomical series.
        subj_id: Subject ID (e.g. 7 becomes "sub-07").
        ses_id: Session ID (e.g. 1 becomes "ses-01").
        project_folder: Project name or full path for the BIDS project.

    Returns:
        Path to the created NIfTI file, or empty string on failure.
    """
    expanded_path = os.path.expanduser(file_of_series)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "create_vmr_dicom_nifti_bids",
                "file_of_series": expanded_path,
                "subj_id": subj_id,
                "ses_id": ses_id,
                "project_folder": project_folder
            },
            timeout=60
        )
        if response.status_code == 200:
            nifti_path = _parse_bv_result(response)
            if nifti_path:
                return f"Success: NIfTI created at '{nifti_path}'."
            return "Warning: NIfTI creation returned an empty path."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def create_vmr_from_bv_raw(
    first_file: str,
    n_slices: int,
    scanner_file_type: str = "DICOM",
    big_endian: bool = False,
    slice_rows: int = 0,
    slice_cols: int = 0,
    bytes_per_pixel: int = 2
) -> str:
    """
    Creates a VMR document from raw MRI files with full parameter control.
    Supports DICOM, ANALYZE, PHILIPS_REC, and GE formats.

    Args:
        first_file: Path to the first raw file of the series.
        n_slices: Number of slices in the 3D volume.
        scanner_file_type: Raw data type ("DICOM", "ANALYZE", "PHILIPS_REC", etc.).
        big_endian: True for big-endian byte order.
        slice_rows: Rows per slice (0 = read from header if possible).
        slice_cols: Columns per slice (0 = read from header if possible).
        bytes_per_pixel: Bytes per pixel, typically 2.
    """
    expanded_path = os.path.expanduser(first_file)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "create_vmr",
                "scanner_file_type": scanner_file_type,
                "first_file": expanded_path,
                "n_slices": n_slices,
                "big_endian": big_endian,
                "slice_rows": slice_rows,
                "slice_cols": slice_cols,
                "bytes_per_pixel": bytes_per_pixel
            },
            timeout=30
        )
        if response.status_code == 200:
            return "Success: VMR document created from raw data."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def create_amr_from_bv_raw(
    first_file: str,
    n_slices: int,
    scanner_file_type: str = "DICOM",
    big_endian: bool = False,
    slice_rows: int = 0,
    slice_cols: int = 0,
    bytes_per_pixel: int = 2
) -> str:
    """
    Creates an AMR document from raw MRI files. AMR documents display
    multi-slice anatomical data and can be used as background for FMR
    functional overlays with interpolated resolution.

    Args:
        first_file: Path to the first raw file of the series.
        n_slices: Number of slices in the volume.
        scanner_file_type: Raw data type ("DICOM", "ANALYZE", "PHILIPS_REC", etc.).
        big_endian: True for big-endian byte order.
        slice_rows: Rows per slice (0 = read from header if possible).
        slice_cols: Columns per slice (0 = read from header if possible).
        bytes_per_pixel: Bytes per pixel, typically 2.
    """
    expanded_path = os.path.expanduser(first_file)
    if not os.path.exists(expanded_path):
        return f"Error: File not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "create_amr",
                "scanner_file_type": scanner_file_type,
                "first_file": expanded_path,
                "n_slices": n_slices,
                "big_endian": big_endian,
                "slice_rows": slice_rows,
                "slice_cols": slice_cols,
                "bytes_per_pixel": bytes_per_pixel
            },
            timeout=30
        )
        if response.status_code == 200:
            return "Success: AMR document created from raw data."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# VMR Document Methods
# ---------------------------------------------------------------------------

@mcp.tool()
def deface_bv_vmr() -> str:
    """
    Defaces the currently active VMR document.
    Requires 1.0mm iso-voxel data. Works in native or MNI space.
    Saves result as '[original-name]_defaced.vmr'.

    Returns:
        True if defacing succeeded, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_deface"},
            timeout=60
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: Defacing complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def transform_bv_vmr_to_std_sag(out_vmr_sag_filename: str) -> str:
    """
    Reorients the active VMR to BrainVoyager standard sagittal orientation
    (radiological convention, right-is-left). Produces a new VMR file.

    Args:
        out_vmr_sag_filename: Output filename (recommended: "[name]_SAG.vmr").

    Returns:
        True if successful, False if already in sagittal orientation.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_transform_to_std_sag",
                "out_vmr_sag_filename": out_vmr_sag_filename
            },
            timeout=60
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: VMR transformed to standard sagittal. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def transform_bv_vmr_to_std_isovoxel(
    out_vmr_iso_filename: str,
    interpolation_method: int = 1
) -> str:
    """
    Resamples the active VMR to 1.0mm iso-voxel resolution in a 256 framing cube.

    Args:
        out_vmr_iso_filename: Output filename (recommended: "[name]_ISO.vmr").
        interpolation_method: 1 = trilinear, 2 = cubic spline, 3 = sinc.

    Returns:
        True if successful, False if already 1mm iso-voxel.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_transform_to_std_isovoxel",
                "out_vmr_iso_filename": out_vmr_iso_filename,
                "interpolation_method": interpolation_method
            },
            timeout=120
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: VMR transformed to 1mm isovoxel. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def transform_bv_vmr_to_isovoxel(
    out_vmr_iso_filename: str,
    target_res: float = 1.0,
    framing_cube_dim: int = 256,
    interpolation_method: int = 1
) -> str:
    """
    Resamples the active VMR to a custom iso-voxel resolution.
    Useful for sub-millimeter data from ultra-high field scanners.

    Args:
        out_vmr_iso_filename: Output filename.
        target_res: Target resolution in mm (e.g. 0.8 for sub-millimeter).
        framing_cube_dim: Framing cube dimension (256, 384, 512, etc.).
        interpolation_method: 1 = trilinear, 2 = cubic spline, 3 = sinc.

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_transform_to_isovoxel",
                "out_vmr_iso_filename": out_vmr_iso_filename,
                "target_res": target_res,
                "framing_cube_dim": framing_cube_dim,
                "interpolation_method": interpolation_method
            },
            timeout=120
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: VMR transformed to isovoxel. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def correct_bv_vmr_intensity_inhomogeneities() -> str:
    """
    Corrects spatial intensity inhomogeneities (bias field) of the active VMR.
    Runs 3 cycles with default parameters. Includes brain extraction.
    Saves results as '[name]_IIHC.vmr' and '[name]_BrainMask.vmr'.
    Operates in-place — the active VMR holds corrected data afterwards.

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_correct_intensity_inhomogeneities"},
            timeout=300
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: IIHC complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def correct_bv_vmr_intensity_inhomogeneities_ext(
    include_brain_extraction: bool = True,
    n_cycles: int = 3,
    tissue_range_thresh: float = 0.25,
    intensity_thresh: float = 0.3,
    fit_polynom_order: int = 3
) -> str:
    """
    Corrects intensity inhomogeneities with full parameter control.
    Estimates and removes a low-frequency 3D bias field iteratively.

    Args:
        include_brain_extraction: Perform skull stripping first (recommended).
        n_cycles: Number of bias field fitting iterations.
        tissue_range_thresh: Threshold for WM/GM detection (recommended: 0.25).
        intensity_thresh: Threshold separating WM from GM (recommended: 0.3).
        fit_polynom_order: Polynomial order for 3D bias field fit (recommended: 3).

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_correct_intensity_inhomogeneities_ext",
                "include_brain_extraction": include_brain_extraction,
                "n_cycles": n_cycles,
                "tissue_range_thresh": tissue_range_thresh,
                "intensity_thresh": intensity_thresh,
                "fit_polynom_order": fit_polynom_order
            },
            timeout=600
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: IIHC (ext) complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def normalize_bv_vmr_to_mni_space() -> str:
    """
    Performs automatic brain normalization of the active VMR to MNI-152 space.
    Requires brain-extracted, inhomogeneity-corrected data.
    Saves MNI VMR and TRF transformation files. Closes native VMR and loads MNI.

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_normalize_to_mni_space"},
            timeout=300
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: MNI normalization complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def auto_acpc_tal_bv_vmr_transformation() -> str:
    """
    Performs automatic ACPC and Talairach transformation of the active VMR.
    Detects mid-sagittal plane, AC/PC points, and cerebrum borders.
    Requires brain-extracted, inhomogeneity-corrected data.
    Saves ACPC/TAL VMRs, TAL file, and TRF transformation files.

    Returns:
        True if successful, False otherwise.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_auto_acpc_tal_transformation"},
            timeout=300
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: ACPC/Talairach transformation complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def get_bv_vmr_voxel_intensity(x: int, y: int, z: int) -> str:
    """
    Returns the intensity value at the given voxel coordinates in the active VMR.
    Note: This is slow for iterating over all voxels.

    Args:
        x: X coordinate (left-to-right in standard orientation).
        y: Y coordinate (posterior-to-anterior).
        z: Z coordinate (inferior-to-superior).

    Returns:
        The intensity value (0-225) at the specified voxel.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_get_voxel_intensity",
                "x": x, "y": y, "z": z
            },
            timeout=10
        )
        if response.status_code == 200:
            value = _parse_bv_result(response)
            return f"Voxel intensity at ({x}, {y}, {z}): {value}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def set_bv_vmr_voxel_intensity(x: int, y: int, z: int, value: int) -> str:
    """
    Sets the intensity value at the given voxel coordinates in the active VMR.
    Note: This is slow for iterating over all voxels.

    Args:
        x: X coordinate (left-to-right in standard orientation).
        y: Y coordinate (posterior-to-anterior).
        z: Z coordinate (inferior-to-superior).
        value: New intensity value (0-225; 226-255 reserved for drawing).
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "vmr_set_voxel_intensity",
                "x": x, "y": y, "z": z, "value": value
            },
            timeout=10
        )
        if response.status_code == 200:
            return f"Success: Voxel ({x}, {y}, {z}) set to {value}."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def create_bv_vmr_mesh_scene() -> str:
    """
    Creates (or retrieves) a MeshScene for the active VMR document.
    The MeshScene enables loading and displaying head/cortex meshes in the 3D Viewer.

    Returns:
        Success/failure message.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_create_mesh_scene"},
            timeout=10
        )
        if response.status_code == 200:
            return "Success: Mesh scene created/retrieved for active VMR."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def update_bv_vmr_viewer() -> str:
    """
    Updates the 3D Viewer (OpenGL) window attached to the active VMR.
    Useful after changing mesh appearance. Usually not needed in auto-update mode.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "vmr_update_viewer"},
            timeout=10
        )
        if response.status_code == 200:
            return "Success: VMR viewer updated."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# DICOM Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def anonymize_bv_dicoms(directory: str, anonymized_patient_name: str) -> str:
    """
    Renames DICOM files to standard format and replaces the patient name
    for anonymization. Files are renamed to:
    PatientsName-SeriesNumber-VolumeNumber-ImageNumber.dcm

    Args:
        directory: Path to the folder containing DICOM files.
        anonymized_patient_name: New patient name (e.g. "P24").
    """
    expanded_dir = os.path.expanduser(directory)
    if not os.path.isdir(expanded_dir):
        return f"Error: Directory not found at '{expanded_dir}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "anonymize_dicoms",
                "path": expanded_dir,
                "patient_name": anonymized_patient_name
            },
            timeout=30
        )
        if response.status_code == 200:
            return f"Success: BrainVoyager is anonymizing DICOMs in '{expanded_dir}'."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def deface_bv_anatomical_dicoms(input_directory: str, output_directory: str) -> str:
    """
    Defaces anatomical DICOM images (3D VMR dataset, 1mm iso voxels required).
    Normalizes to MNI space, applies a defacing mask in native space, and
    saves defaced copies prefixed with "defaced_" to the output directory.

    Args:
        input_directory: Folder containing the original 3D anatomical DICOMs.
        output_directory: Folder where defaced DICOMs will be saved.
    """
    expanded_input = os.path.expanduser(input_directory)
    expanded_output = os.path.expanduser(output_directory)
    if not os.path.isdir(expanded_input):
        return f"Error: Input directory not found at '{expanded_input}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "deface_anat_dicoms",
                "input_directory": expanded_input,
                "output_directory": expanded_output
            },
            timeout=120
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: Defacing complete. Result: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Log Pane Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def show_bv_log_pane() -> str:
    """
    Shows the BrainVoyager Log pane.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "show_log_pane"},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: Log pane shown."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def hide_bv_log_pane() -> str:
    """
    Hides the BrainVoyager Log pane.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "hide_log_pane"},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: Log pane hidden."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def print_to_bv_log(text: str) -> str:
    """
    Prints a message to the BrainVoyager Log pane.

    Args:
        text: The text to print. Simple HTML formatting is supported.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "print_to_log", "text": text},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: Printed to BrainVoyager log."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Shell Command
# ---------------------------------------------------------------------------

@mcp.tool()
def run_bv_shell_command(shell_command: str) -> str:
    """
    Runs a shell command and returns its stdout output.
    Note: BrainVoyager will block until the command completes.

    Args:
        shell_command: The shell command to execute.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "run_cmd", "shell_command": shell_command},
            timeout=30
        )
        if response.status_code == 200:
            return _parse_bv_result(response)
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Application Control
# ---------------------------------------------------------------------------

@mcp.tool()
def exit_bv() -> str:
    """
    Quits BrainVoyager. Use with caution — only call at the end of a script.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "exit"},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: BrainVoyager is shutting down."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Dialog / Message Commands
# ---------------------------------------------------------------------------

@mcp.tool()
def show_bv_message_box(message: str) -> str:
    """
    Shows a message box in BrainVoyager with the given text.

    Args:
        message: The message to display.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "show_message_box", "message": message},
            timeout=5
        )
        if response.status_code == 200:
            return "Success: Message box shown."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def show_bv_timeout_message_box(message: str, duration: int = 3000) -> str:
    """
    Shows a message box that auto-closes after the specified duration.

    Args:
        message: The message to display.
        duration: Time in milliseconds before the box auto-closes (default 3000).
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "show_timeout_message_box",
                "message": message,
                "duration": duration
            },
            timeout=5
        )
        if response.status_code == 200:
            result = _parse_bv_result(response)
            return f"Success: Timeout message box shown. User response: {result}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# Window Control
# ---------------------------------------------------------------------------

@mcp.tool()
def move_bv_window(new_x: int, new_y: int) -> str:
    """
    Moves the BrainVoyager main window to the specified screen coordinates.

    Args:
        new_x: New X position in pixels.
        new_y: New Y position in pixels.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "move_window", "new_x": new_x, "new_y": new_y},
            timeout=5
        )
        if response.status_code == 200:
            return f"Success: Window moved to ({new_x}, {new_y})."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def resize_bv_window(new_width: int, new_height: int) -> str:
    """
    Resizes the BrainVoyager main window.

    Args:
        new_width: New width in pixels.
        new_height: New height in pixels.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "resize_window",
                "new_width": new_width,
                "new_height": new_height
            },
            timeout=5
        )
        if response.status_code == 200:
            return f"Success: Window resized to {new_width}x{new_height}."
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# File / Directory Choosers
# ---------------------------------------------------------------------------

@mcp.tool()
def choose_bv_directory(instruction: str = "Select a directory") -> str:
    """
    Opens a directory chooser dialog in BrainVoyager.

    Args:
        instruction: Prompt text shown in the dialog.

    Returns:
        The path selected by the user, or an empty string if cancelled.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "choose_directory", "instruction": instruction},
            timeout=60
        )
        if response.status_code == 200:
            chosen = _parse_bv_result(response)
            return chosen if chosen else "(User cancelled)"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


@mcp.tool()
def choose_bv_file(instruction: str = "Select a file", filter: str = "*") -> str:
    """
    Opens a file chooser dialog in BrainVoyager.

    Args:
        instruction: Prompt text shown in the dialog.
        filter: File type filter pattern (e.g. "*.vmr").

    Returns:
        The file path selected by the user, or an empty string if cancelled.
    """
    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={
                "action": "choose_file",
                "instruction": instruction,
                "filter": filter
            },
            timeout=60
        )
        if response.status_code == 200:
            chosen = _parse_bv_result(response)
            return chosen if chosen else "(User cancelled)"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


# ---------------------------------------------------------------------------
# MDM / VTCs
# ---------------------------------------------------------------------------

@mcp.tool()
def get_vtcs_of_mdm(mdm_file: str) -> str:
    """
    Returns the list of VTC file paths referenced in an MDM file.

    Args:
        mdm_file: Path to the .mdm file.
    """
    expanded_path = os.path.expanduser(mdm_file)
    if not os.path.exists(expanded_path):
        return f"Error: MDM file not found at '{expanded_path}'."

    try:
        response = requests.post(
            BV_LISTENER_URL,
            json={"action": "get_vtcs_of_mdm", "mdm_file": expanded_path},
            timeout=10
        )
        if response.status_code == 200:
            return f"VTCs in MDM:\n{_parse_bv_result(response)}"
        return f"Error from BrainVoyager: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection Error: Is the Qt listener running in BrainVoyager?"


if __name__ == "__main__":
    mcp.run()