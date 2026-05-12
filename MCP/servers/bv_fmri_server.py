"""BV fMRI MCP Server — FMR creation, preprocessing, VTC, MDM, DMR & project."""
from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_client import call_bv, call_bv_with_path

mcp = FastMCP(
    "BrainVoyager fMRI",
    instructions=(
        "Most operations are fast. Motion correction, spatial/temporal "
        "smoothing, and high-pass filtering on large datasets may take longer. "
        "Long-running tools accept a timeout_seconds parameter."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════
# FMR Document Creation
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def create_fmr_from_bv_dicom(
    file_of_series: str, fmr_stc_filename: str, target_folder: str,
    protocol_file: str = "",
) -> str:
    """Create a FMR document from a DICOM functional series.

    Only needs one file of the series; all parameters are read from the
    DICOM header.  Supports single-image, Siemens mosaic, and multi-frame
    enhanced DICOM.

    Args:
        file_of_series: Path to one DICOM file of the functional series.
        fmr_stc_filename: Name for the output .stc file (e.g. "myrun.stc").
        target_folder: Folder where the FMR/STC files will be created.
        protocol_file: Optional protocol file for slice timing correction.
    """
    return call_bv_with_path(
        "create_fmr_dicom", file_of_series, timeout=60,
        fmr_stc_filename=fmr_stc_filename, target_folder=target_folder,
        protocol_file=protocol_file)


@mcp.tool()
def create_fmr_nifti_bids_from_bv_dicom(
    file_of_series: str, subj_id: int, ses_id: int, run_id: int,
    task_name: str, project_folder: str, protocol_file: str = "",
) -> str:
    """Create a BIDS-compliant NIfTI from functional DICOM.

    Args:
        file_of_series: Path to one DICOM of the functional series.
        subj_id: Subject number (e.g. 7 → "sub-07").
        ses_id: Session number (e.g. 1 → "ses-01").
        run_id: Run number.
        task_name: BIDS task label (e.g. "rest", "facerecognition").
        project_folder: BIDS project root folder path.
        protocol_file: Optional protocol file for slice timing.

    Returns:
        Path to the created NIfTI file on success.
    """
    return call_bv_with_path(
        "create_fmr_dicom_nifti_bids", file_of_series, timeout=120,
        subj_id=subj_id, ses_id=ses_id, run_id=run_id, task_name=task_name,
        project_folder=project_folder, protocol_file=protocol_file)


# ═══════════════════════════════════════════════════════════════════════════
# FMR Preprocessing Pipeline
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def fmr_correct_motion(timeout_seconds: int = 120) -> str:
    """3D rigid-body motion correction on the active FMR document.

    Aligns all volumes to the first volume. Uses trilinear-sinc
    interpolation by default.  The STC data is modified in-place.

    Usually fast (seconds).  Increase timeout_seconds for long runs."""
    return call_bv("fmr_correct_motion", timeout=timeout_seconds)


@mcp.tool()
def fmr_correct_motion_to_vol(
    target_vol_idx: int, timeout_seconds: int = 120,
) -> str:
    """3D motion correction aligning to a specific target volume.

    Args:
        target_vol_idx: 0-based index of the volume to align to.
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_correct_motion_to_vol", timeout=timeout_seconds,
                   target_vol_idx=target_vol_idx)


@mcp.tool()
def fmr_correct_slice_timing(
    interpolation_method: int = 1, timeout_seconds: int = 120,
) -> str:
    """Slice timing correction on the active FMR document.

    Uses the timing table embedded in the DICOM header — handles single
    and multi-band data automatically.  Resamples each slice's time course
    to a common reference time point.

    Args:
        interpolation_method: 1=trilinear, 2=cubic spline, 3=sinc.
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_correct_slicetiming", timeout=timeout_seconds,
                   interpolation_method=interpolation_method)


@mcp.tool()
def fmr_smooth_spatial(
    gauss_fwhm: float = 4.0, fwhm_unit: str = "mm",
    timeout_seconds: int = 120,
) -> str:
    """3D Gaussian spatial smoothing on the active FMR document.

    Args:
        gauss_fwhm: Full width at half maximum (default 4.0).
        fwhm_unit: "mm" (millimeters) or "voxel".
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_smooth_spatial", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def fmr_smooth_temporal(
    gauss_fwhm: float = 2.0, fwhm_unit: str = "data_points",
    timeout_seconds: int = 120,
) -> str:
    """Gaussian temporal smoothing on the active FMR document.

    Args:
        gauss_fwhm: Full width at half maximum in data points (default 2).
        fwhm_unit: "data_points" or "ms".
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_smooth_temporal", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def fmr_filter_highpass_glm_fourier(
    n_cycles: int = 3, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drifts using a GLM with sine/cosine regressors.

    Args:
        n_cycles: Number of sine/cosine cycles to remove (default 3).
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_filter_highpass_fourier", timeout=timeout_seconds,
                   n_cycles=n_cycles)


@mcp.tool()
def fmr_filter_highpass_glm_dct(
    n_basis_functions: int = 2, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drifts using a GLM with DCT basis functions.

    Args:
        n_basis_functions: Number of DCT bases to remove (default 2).
        timeout_seconds: Max seconds to wait."""
    return call_bv("fmr_filter_highpass_dct", timeout=timeout_seconds,
                   n_basis_functions=n_basis_functions)


# ═══════════════════════════════════════════════════════════════════════════
# MDM / VTC
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def get_vtcs_of_mdm(mdm_file: str) -> str:
    """Return every VTC file path referenced inside a .mdm file."""
    return call_bv_with_path("get_vtcs_of_mdm", mdm_file, timeout=10)


# ═══════════════════════════════════════════════════════════════════════════
# TODO — populate as needed
# ═══════════════════════════════════════════════════════════════════════════
#
#   VTC:  link_vtc, save_vtc, create_vtc_in_native_space,
#         coregister_fmr_to_vmr, coregister_fmr_to_vmr_using_bbr
#   DMR:  create_dmr_dicom, create_dmr_dicom_nifti_bids, create_dmr
#   Mesh: reconstruct_mesh, smooth_geometry, inflate_geometry,
#         inflate_geometry_to_sphere, shrink_wrap_morph, create_sphere_mesh
#   Proj: create_project, subject_data, group_data, workflow.run, connect
#


if __name__ == "__main__":
    mcp.run()
