"""BV fMRI MCP Server — FMR creation, preprocessing, VTC, MDM, DMR & project."""
from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_client import call_bv, call_bv_with_path

mcp = FastMCP(
    "BrainVoyager fMRI",
    instructions=(
        "Most operations are fast. VTC creation, coregistration, and "
        "smoothing on large datasets may take minutes. Long-running tools "
        "accept a timeout_seconds parameter."
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
    """Create an FMR document from a DICOM functional series.

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
        subj_id: Subject number (e.g. 7 -> "sub-07").
        ses_id: Session number (e.g. 1 -> "ses-01").
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
    """3D rigid-body motion correction on the active FMR.

    Aligns all volumes to the first volume using trilinear-sinc
    interpolation.  The STC data is modified in-place."""
    return call_bv("fmr_correct_motion", timeout=timeout_seconds)


@mcp.tool()
def fmr_correct_motion_to_vol(
    target_vol_idx: int, timeout_seconds: int = 120,
) -> str:
    """3D motion correction aligning to a specific target volume.

    Args:
        target_vol_idx: 0-based index of the volume to align to."""
    return call_bv("fmr_correct_motion_to_vol", timeout=timeout_seconds,
                   target_vol_idx=target_vol_idx)


@mcp.tool()
def fmr_correct_slice_timing(
    interpolation_method: int = 1, timeout_seconds: int = 120,
) -> str:
    """Slice timing correction on the active FMR.

    Uses the timing table from the DICOM header — handles single and
    multi-band data automatically.

    Args:
        interpolation_method: 1=trilinear, 2=cubic spline, 3=sinc."""
    return call_bv("fmr_correct_slicetiming", timeout=timeout_seconds,
                   interpolation_method=interpolation_method)


@mcp.tool()
def fmr_smooth_spatial(
    gauss_fwhm: float = 4.0, fwhm_unit: str = "mm",
    timeout_seconds: int = 120,
) -> str:
    """3D Gaussian spatial smoothing on the active FMR.

    Args:
        gauss_fwhm: Full width at half maximum (default 4.0).
        fwhm_unit: "mm" or "voxel"."""
    return call_bv("fmr_smooth_spatial", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def fmr_smooth_temporal(
    gauss_fwhm: float = 2.0, fwhm_unit: str = "data_points",
    timeout_seconds: int = 120,
) -> str:
    """Gaussian temporal smoothing on the active FMR.

    Args:
        gauss_fwhm: FWHM in data points (default 2).
        fwhm_unit: "data_points" or "ms"."""
    return call_bv("fmr_smooth_temporal", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def fmr_filter_highpass_glm_fourier(
    n_cycles: int = 3, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drift from FMR (sine/cosine GLM).

    Args:
        n_cycles: Number of cycles to remove (default 3)."""
    return call_bv("fmr_filter_highpass_fourier", timeout=timeout_seconds,
                   n_cycles=n_cycles)


@mcp.tool()
def fmr_filter_highpass_glm_dct(
    n_basis_functions: int = 2, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drift from FMR (DCT GLM).

    Args:
        n_basis_functions: Number of DCT bases to remove (default 2)."""
    return call_bv("fmr_filter_highpass_dct", timeout=timeout_seconds,
                   n_basis_functions=n_basis_functions)


# ═══════════════════════════════════════════════════════════════════════════
# VTC — Coregistration & VTC Creation
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def vtc_link(vtc_file: str) -> str:
    """Link a .vtc file to the active VMR document."""
    return call_bv("vtc_link", timeout=10, vtc_file=vtc_file)


@mcp.tool()
def vtc_save(vtc_file: str) -> str:
    """Save VTC data from the active VMR to disk."""
    return call_bv("vtc_save", timeout=30, vtc_file=vtc_file)


@mcp.tool()
def vtc_coregister_fmr_to_vmr(
    fmr_file: str, iihc_func: bool = False, use_attached_amr: int = 0,
    timeout_seconds: int = 300,
) -> str:
    """Coregister an FMR to the active VMR (intensity-gradient matching).

    Uses DICOM header alignment + iterative intensity matching.
    Produces IA and FA .trf transformation files.

    Args:
        fmr_file: Path to the FMR file to coregister.
        iihc_func: Run IIHC on the first functional volume first.
        use_attached_amr: 0=first vol as reference, 1=attached AMR.
        timeout_seconds: Max seconds to wait (default 300)."""
    return call_bv("vtc_coregister_fmr", timeout=timeout_seconds,
                   fmr_file=fmr_file, iihc_func=iihc_func,
                   use_attached_amr=use_attached_amr)


@mcp.tool()
def vtc_coregister_fmr_to_vmr_bbr(
    fmr_file: str, timeout_seconds: int = 300,
) -> str:
    """Coregister an FMR to the active VMR (boundary-based registration).

    More accurate than intensity-based for some contrasts, but slower.

    Args:
        fmr_file: Path to the FMR file to coregister.
        timeout_seconds: Max seconds to wait (default 300)."""
    return call_bv("vtc_coregister_fmr_bbr", timeout=timeout_seconds,
                   fmr_file=fmr_file)


@mcp.tool()
def vtc_create_in_native_space(
    fmr_file: str, coreg_ia_trf_file: str, coreg_fa_trf_file: str,
    vtc_file: str, res_to_anat: int = 1, interpolation_method: int = 1,
    bounding_box_intensity_threshold: int = 100, data_type: int = 2,
    timeout_seconds: int = 300,
) -> str:
    """Transform FMR-STC into native VMR space, creating a .vtc file.

    Args:
        fmr_file: Path to the preprocessed FMR file.
        coreg_ia_trf_file: IA coregistration .trf file.
        coreg_fa_trf_file: FA coregistration .trf file.
        vtc_file: Output .vtc filename.
        res_to_anat: Resolution relative to VMR (1=same, 2=double).
        interpolation_method: 1=trilinear, 2=cubic, 3=sinc.
        bounding_box_intensity_threshold: VMR intensity for bounding box.
        data_type: 1=uint8, 2=uint16, 3=float32.
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_create_native", timeout=timeout_seconds,
                   fmr_file=fmr_file, coreg_ia_trf_file=coreg_ia_trf_file,
                   coreg_fa_trf_file=coreg_fa_trf_file, vtc_file=vtc_file,
                   res_to_anat=res_to_anat,
                   interpolation_method=interpolation_method,
                   bounding_box_intensity_threshold=bounding_box_intensity_threshold,
                   data_type=data_type)


@mcp.tool()
def vtc_create_in_mni_space(
    fmr_file: str, coreg_ia_trf_file: str, coreg_fa_trf_file: str,
    mni_trf_file: str, vtc_file: str, res_to_anat: int = 1,
    interpolation_method: int = 1,
    bounding_box_intensity_threshold: int = 100, data_type: int = 2,
    timeout_seconds: int = 300,
) -> str:
    """Transform FMR-STC into MNI space, creating a .vtc file.

    Args:
        fmr_file: Path to the preprocessed FMR file.
        coreg_ia_trf_file: IA .trf file.
        coreg_fa_trf_file: FA .trf file.
        mni_trf_file: MNI normalization .trf file.
        vtc_file: Output .vtc filename.
        res_to_anat: Resolution (1, 2, 3).
        interpolation_method: 1=trilinear, 2=cubic, 3=sinc.
        bounding_box_intensity_threshold: Intensity threshold.
        data_type: 1=uint8, 2=uint16, 3=float32.
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_create_mni", timeout=timeout_seconds,
                   fmr_file=fmr_file, coreg_ia_trf_file=coreg_ia_trf_file,
                   coreg_fa_trf_file=coreg_fa_trf_file,
                   mni_trf_file=mni_trf_file, vtc_file=vtc_file,
                   res_to_anat=res_to_anat,
                   interpolation_method=interpolation_method,
                   bounding_box_intensity_threshold=bounding_box_intensity_threshold,
                   data_type=data_type)


@mcp.tool()
def vtc_create_in_tal_space(
    fmr_file: str, coreg_ia_trf_file: str, coreg_fa_trf_file: str,
    acpc_trf_file: str, tal_file: str, vtc_file: str,
    res_to_anat: int = 1, interpolation_method: int = 1,
    bounding_box_intensity_threshold: int = 100, data_type: int = 2,
    timeout_seconds: int = 300,
) -> str:
    """Transform FMR-STC into Talairach space, creating a .vtc file.

    Args:
        fmr_file: Path to the preprocessed FMR file.
        coreg_ia_trf_file: IA .trf file.
        coreg_fa_trf_file: FA .trf file.
        acpc_trf_file: AC-PC .trf file.
        tal_file: Talairach .tal file.
        vtc_file: Output .vtc filename.
        res_to_anat: Resolution (1, 2, 3).
        interpolation_method: 1=trilinear, 2=cubic, 3=sinc.
        bounding_box_intensity_threshold: Intensity threshold.
        data_type: 1=uint8, 2=uint16, 3=float32.
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_create_tal", timeout=timeout_seconds,
                   fmr_file=fmr_file, coreg_ia_trf_file=coreg_ia_trf_file,
                   coreg_fa_trf_file=coreg_fa_trf_file,
                   acpc_trf_file=acpc_trf_file, tal_file=tal_file,
                   vtc_file=vtc_file, res_to_anat=res_to_anat,
                   interpolation_method=interpolation_method,
                   bounding_box_intensity_threshold=bounding_box_intensity_threshold,
                   data_type=data_type)


# ═══════════════════════════════════════════════════════════════════════════
# VTC Preprocessing (smoothing / filtering on linked VTC)
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def vtc_smooth_spatial(
    gauss_fwhm: float = 4.0, fwhm_unit: str = "mm",
    timeout_seconds: int = 120,
) -> str:
    """3D Gaussian spatial smoothing on the VTC attached to active VMR.

    Args:
        gauss_fwhm: Full width at half maximum (default 4.0).
        fwhm_unit: "mm" or "voxel".
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_smooth_spatial", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def vtc_smooth_temporal(
    gauss_fwhm: float = 2.0, fwhm_unit: str = "data_points",
    timeout_seconds: int = 120,
) -> str:
    """Gaussian temporal smoothing on the VTC attached to active VMR.

    Args:
        gauss_fwhm: FWHM in data points (default 2).
        fwhm_unit: "data_points" or "ms".
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_smooth_temporal", timeout=timeout_seconds,
                   gauss_fwhm=gauss_fwhm, fwhm_unit=fwhm_unit)


@mcp.tool()
def vtc_filter_highpass_glm_fourier(
    n_cycles: int = 3, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drift from VTC (sine/cosine GLM).

    Args:
        n_cycles: Number of cycles to remove (default 3).
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_filter_highpass_fourier",
                   timeout=timeout_seconds, n_cycles=n_cycles)


@mcp.tool()
def vtc_filter_highpass_glm_dct(
    n_basis_functions: int = 2, timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drift from VTC (DCT GLM).

    Args:
        n_basis_functions: Number of DCT bases to remove (default 2).
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_filter_highpass_dct",
                   timeout=timeout_seconds, n_basis_functions=n_basis_functions)


@mcp.tool()
def vtc_filter_highpass_fft(
    highpass: float = 0.008, highpass_unit: str = "Hz",
    timeout_seconds: int = 120,
) -> str:
    """Remove low-frequency drift from VTC using FFT.

    Removes linear trend, FFT-transforms, zeroes low frequencies, IFFT.

    Args:
        highpass: Frequency cut-off (default 0.008 Hz ~ 125 s).
        highpass_unit: "Hz" or "s" (period in seconds).
        timeout_seconds: Max seconds to wait."""
    return call_bv("vtc_filter_highpass_fft", timeout=timeout_seconds,
                   highpass=highpass, highpass_unit=highpass_unit)


# ═══════════════════════════════════════════════════════════════════════════
# MDM
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def get_vtcs_of_mdm(mdm_file: str) -> str:
    """Return every VTC file path referenced inside a .mdm file."""
    return call_bv_with_path("get_vtcs_of_mdm", mdm_file, timeout=10)


# ═══════════════════════════════════════════════════════════════════════════
# TODO — DMR, Mesh, Project
# ═══════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    mcp.run()
