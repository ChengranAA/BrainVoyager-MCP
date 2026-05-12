"""BV Anatomy MCP Server — VMR creation, preprocessing, mesh & MP2RAGE."""
import os
from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_client import call_bv, call_bv_with_path

mcp = FastMCP(
    "BrainVoyager Anatomy",
    instructions=(
        "Most operations are fast (BV C++ core does the heavy lifting). "
        "IIHC, MNI normalization, and MP2RAGE denoising on large datasets "
        "may take longer. Long-running tools accept a timeout_seconds param."
    ),
)


@mcp.tool()
def create_vmr_from_bv_dicom(file_of_series: str) -> str:
    """Create a VMR document from one DICOM file of a 3D anatomical series."""
    return call_bv_with_path(
        "create_vmr_dicom", file_of_series, timeout=30, file_of_series=file_of_series)


@mcp.tool()
def create_vmr_nifti_bids_from_bv_dicom(
    file_of_series: str, subj_id: int, ses_id: int, project_folder: str,
) -> str:
    """Create a BIDS-compliant NIfTI from anatomical DICOMs."""
    return call_bv_with_path(
        "create_vmr_dicom_nifti_bids", file_of_series, timeout=60,
        subj_id=subj_id, ses_id=ses_id, project_folder=project_folder)


@mcp.tool()
def create_vmr_from_bv_raw(
    first_file: str, n_slices: int, scanner_file_type: str = "DICOM",
    big_endian: bool = False, slice_rows: int = 0, slice_cols: int = 0,
    bytes_per_pixel: int = 2,
) -> str:
    """Create a VMR from raw MRI files (DICOM, ANALYZE, PHILIPS_REC, GE…)."""
    return call_bv_with_path(
        "create_vmr", first_file, timeout=30,
        scanner_file_type=scanner_file_type, n_slices=n_slices,
        big_endian=big_endian, slice_rows=slice_rows, slice_cols=slice_cols,
        bytes_per_pixel=bytes_per_pixel)


@mcp.tool()
def create_amr_from_bv_raw(
    first_file: str, n_slices: int, scanner_file_type: str = "DICOM",
    big_endian: bool = False, slice_rows: int = 0, slice_cols: int = 0,
    bytes_per_pixel: int = 2,
) -> str:
    """Create an AMR document from raw MRI files."""
    return call_bv_with_path(
        "create_amr", first_file, timeout=30,
        scanner_file_type=scanner_file_type, n_slices=n_slices,
        big_endian=big_endian, slice_rows=slice_rows, slice_cols=slice_cols,
        bytes_per_pixel=bytes_per_pixel)


# ── VMR Preprocessing ─────────────────────────────────────────────────────


@mcp.tool()
def deface_bv_vmr(timeout_seconds: int = 60) -> str:
    """Deface the active VMR (remove facial features for anonymization)."""
    return call_bv("vmr_deface", timeout=timeout_seconds)


@mcp.tool()
def transform_bv_vmr_to_std_sag(
    out_vmr_sag_filename: str, timeout_seconds: int = 60,
) -> str:
    """Reorient VMR to standard sagittal (radiological) orientation."""
    return call_bv("vmr_transform_to_std_sag", timeout=timeout_seconds,
                   out_vmr_sag_filename=out_vmr_sag_filename)


@mcp.tool()
def transform_bv_vmr_to_std_isovoxel(
    out_vmr_iso_filename: str, interpolation_method: int = 1,
    timeout_seconds: int = 60,
) -> str:
    """Resample VMR to 1.0 mm iso-voxel in a 256³ framing cube."""
    return call_bv("vmr_transform_to_std_isovoxel", timeout=timeout_seconds,
                   out_vmr_iso_filename=out_vmr_iso_filename,
                   interpolation_method=interpolation_method)


@mcp.tool()
def transform_bv_vmr_to_isovoxel(
    out_vmr_iso_filename: str, target_res: float = 1.0,
    framing_cube_dim: int = 256, interpolation_method: int = 1,
    timeout_seconds: int = 60,
) -> str:
    """Resample VMR to a custom iso-voxel resolution."""
    return call_bv("vmr_transform_to_isovoxel", timeout=timeout_seconds,
                   out_vmr_iso_filename=out_vmr_iso_filename,
                   target_res=target_res, framing_cube_dim=framing_cube_dim,
                   interpolation_method=interpolation_method)


@mcp.tool()
def correct_bv_vmr_intensity_inhomogeneities(timeout_seconds: int = 60) -> str:
    """Correct IIHC on the active VMR (3 cycles + brain extraction).

    Usually fast (seconds). Increase timeout_seconds for large 7T data."""
    return call_bv("vmr_correct_intensity_inhomogeneities",
                   timeout=timeout_seconds)


@mcp.tool()
def correct_bv_vmr_intensity_inhomogeneities_ext(
    include_brain_extraction: bool = True, n_cycles: int = 3,
    tissue_range_thresh: float = 0.25, intensity_thresh: float = 0.3,
    fit_polynom_order: int = 3, timeout_seconds: int = 120,
) -> str:
    """Correct IIHC with full parameter control.

    Usually fast (seconds). Increase timeout_seconds for large data."""
    return call_bv("vmr_correct_intensity_inhomogeneities_ext",
                   timeout=timeout_seconds,
                   include_brain_extraction=include_brain_extraction,
                   n_cycles=n_cycles, tissue_range_thresh=tissue_range_thresh,
                   intensity_thresh=intensity_thresh,
                   fit_polynom_order=fit_polynom_order)


@mcp.tool()
def normalize_bv_vmr_to_mni_space(timeout_seconds: int = 120) -> str:
    """Normalize VMR to MNI-152 space. Requires IIHC first.

    Usually fast (under a minute). Increase timeout_seconds for large data."""
    return call_bv("vmr_normalize_to_mni_space", timeout=timeout_seconds)


@mcp.tool()
def auto_acpc_tal_bv_vmr_transformation(timeout_seconds: int = 120) -> str:
    """Auto AC-PC and Talairach transformation. Requires IIHC first.

    Usually fast (under a minute). Increase timeout_seconds for large data."""
    return call_bv("vmr_auto_acpc_tal_transformation",
                   timeout=timeout_seconds)


# ── Voxel Access ──────────────────────────────────────────────────────────


@mcp.tool()
def get_bv_vmr_voxel_intensity(x: int, y: int, z: int) -> str:
    """Read intensity at (x, y, z) in active VMR. Slow for iteration."""
    return call_bv("vmr_get_voxel_intensity", timeout=10, x=x, y=y, z=z)


@mcp.tool()
def set_bv_vmr_voxel_intensity(x: int, y: int, z: int, value: int) -> str:
    """Set intensity at (x, y, z). Value 0-225. Slow for iteration."""
    return call_bv("vmr_set_voxel_intensity", timeout=10,
                   x=x, y=y, z=z, value=value)


# ── Mesh / 3D Viewer ──────────────────────────────────────────────────────


@mcp.tool()
def create_bv_vmr_mesh_scene() -> str:
    """Create/retrieve a MeshScene for the active VMR (enables 3D Viewer)."""
    return call_bv("vmr_create_mesh_scene", timeout=10)


@mcp.tool()
def update_bv_vmr_viewer() -> str:
    """Refresh the OpenGL 3D Viewer for the active VMR."""
    return call_bv("vmr_update_viewer", timeout=10)


# ── MP2RAGE Denoising ─────────────────────────────────────────────────────


@mcp.tool()
def run_mp2rage_denoise(
    chosen_factor: float, path_uni: str, path_inv1: str, path_inv2: str,
    uniden_filename: str = "uniden.v16", save_vmr: bool = True,
    timeout_seconds: int = 120,
) -> str:
    """Denoise MP2RAGE MRI (salt-and-pepper background noise removal).

    Does NumPy math — increase timeout_seconds for large 7T datasets."""
    expanded_uni = os.path.expanduser(path_uni)
    expanded_inv1 = os.path.expanduser(path_inv1)
    expanded_inv2 = os.path.expanduser(path_inv2)
    missing = [p for p in [expanded_uni, expanded_inv1, expanded_inv2]
               if not os.path.exists(p)]
    if missing:
        return f"Error: Missing files: {', '.join(missing)}"
    return call_bv("mp2rage_denoise", timeout=timeout_seconds,
                   chosen_factor=chosen_factor, path_uni=expanded_uni,
                   path_inv1=expanded_inv1, path_inv2=expanded_inv2,
                   uniden_filename=uniden_filename, save_vmr=save_vmr)


if __name__ == "__main__":
    mcp.run()
