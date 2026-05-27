---
name: bv-anatomical-pipeline
description: >
  Full BrainVoyager anatomical preprocessing pipeline: VMR creation from DICOM,
  MP2RAGE denoising (UNI/INV1/INV2 → uniden), intensity inhomogeneity correction
  (IIHC) with brain extraction, isovoxel resampling, MNI normalization, Talairach
  transformation, and defacing. Use when the user needs to "process anatomical data,"
  "create VMR," "denoise MP2RAGE," "correct bias field," "normalize to MNI," "AC-PC
  transform," or "prepare anatomy for coregistration."
compatibility: Requires BrainVoyager MCP (Anatomy server). For MP2RAGE: Python with bvbabel and nibabel. DICOM data must be renamed.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager Anatomical Pipeline

Process high-resolution anatomical data: VMR creation → MP2RAGE denoising → IIHC → isovoxel → normalization.

## Pipeline overview

```
DICOM (anatomical series)
  │
  ├─ [1] Create VMR                    ← create_vmr_from_bv_dicom
  ├─ [2] MP2RAGE denoising (optional)  ← run_mp2rage_denoise
  ├─ [3] IIHC + brain extraction       ← correct_bv_vmr_intensity_inhomogeneities
  ├─ [4] Isovoxel resampling           ← transform_bv_vmr_to_std_isovoxel
  ├─ [5] Reorient to sagittal          ← transform_bv_vmr_to_std_sag (optional)
  ├─ [6] MNI normalization             ← normalize_bv_vmr_to_mni_space
  ├─ [7] AC-PC + Talairach             ← auto_acpc_tal_bv_vmr_transformation
  └─ [8] Deface                        ← deface_bv_vmr
  ▼
VMR ready for coregistration / mesh reconstruction
```

**Not all steps are required for every project.** The minimum is typically: [1] → [3] → [4] → [6]. MP2RAGE denoising [2] is only for MP2RAGE acquisitions; Talairach [7] and defacing [8] are project-dependent.

## Step 1: Create VMR from DICOM

```python
create_vmr_from_bv_dicom(
    file_of_series="/path/to/dicoms/Subj01-0005-0001-00001.dcm"
)
```

Only one DICOM file is needed — BV auto-detects all parameters. For non-DICOM or raw data:

```python
create_vmr_from_bv_raw(
    first_file="/path/to/raw/first_slice.img",
    n_slices=192,
    scanner_file_type="DICOM",  # or ANALYZE, PHILIPS_REC, GE
    big_endian=False,
    slice_rows=256,
    slice_cols=256,
    bytes_per_pixel=2
)
```

Save with a descriptive name:

```python
save_active_document_as(file_name="/path/to/Subj01_UNI.vmr")
```

## Step 2: MP2RAGE denoising (if applicable)

For MP2RAGE acquisitions, denoise the UNI image using INV1 and INV2:

```python
run_mp2rage_denoise(
    chosen_factor=10.0,
    path_uni="/path/to/UNI.v16",    # or .vmr
    path_inv1="/path/to/INV1.v16",
    path_inv2="/path/to/INV2.v16",
    uniden_filename="uniden.v16",
    save_vmr=True
)
```

### How MP2RAGE denoising works

The MP2RAGE UNI image has excellent T1 contrast but suffers from salt-and-pepper background noise. The denoising algorithm:
1. Computes a robust phase-sensitive estimate of INV1 using both INV1 and INV2
2. Estimates background noise level from the edge of INV2
3. Applies a robust combination: `(conj(INV1)*INV2 - β) / (INV1² + INV2² + 2β)`
4. The `chosen_factor` multiplies the noise estimate — typical range is 5-20

### Choosing chosen_factor

| Factor | Effect |
|--------|--------|
| 5-10 | Conservative — some background noise remains |
| 10-20 | Aggressive — cleaner background, may erode tissue edges |
| 10 | Default — works well for most 3T MP2RAGE |

**Start with 10** and inspect the result. If background noise persists, increase; if tissue edges look eroded, decrease.

### Input file requirements

- **UNI, INV1, INV2** MUST be V16 files (2-byte integer, float values mapped to 0-4095).
  **CRITICAL**: Passing `.vmr` paths to `run_mp2rage_denoise` silently produces a corrupted
  output (e.g., 409KB VMR instead of 24MB). The tool does NumPy math on uint16 raw
  data, which VMR (uint8 byte-packed) cannot provide.
- To create V16 from VMR: open each VMR in BV first — BV auto-creates `*.v16`
  companions on disk. Then pass the `.v16` paths.
- All three must have matching dimensions; mismatches in phase-encode direction are auto-corrected

## Step 3: Intensity inhomogeneity correction (IIHC)

Correct the bias field (smooth intensity variation from coil sensitivity):

```python
# Open the VMR first
open_bv_document("/path/to/Subj01_UNI.vmr")

# Standard IIHC: 3 cycles, includes brain extraction
correct_bv_vmr_intensity_inhomogeneities(timeout_seconds=120)

# Output: "Subj01_UNI_IIHC.vmr"
```

### Extended IIHC with custom parameters

For fine control (e.g., 7T data, poor brain extraction):

```python
correct_bv_vmr_intensity_inhomogeneities_ext(
    include_brain_extraction=True,  # skull-strip first
    n_cycles=8,                     # more cycles for severe inhomogeneity
    tissue_range_thresh=0.25,       # threshold to detect tissue types
    intensity_thresh=0.3,           # WM/GM boundary threshold
    fit_polynom_order=3,            # polynomial order for bias field (3=cubic)
    timeout_seconds=300
)
```

### IIHC parameter guidelines

| Parameter | Standard (3T) | 7T / severe inhomogeneity |
|-----------|---------------|---------------------------|
| n_cycles | 3 | 6-8 |
| tissue_range_thresh | 0.25 | 0.20 (wider range) |
| intensity_thresh | 0.3 | 0.25 (lower threshold) |
| fit_polynom_order | 3 | 3-4 |

**Gotcha**: IIHC requires a V16 file alongside the VMR. If no V16 exists, BV will create one from the VMR data automatically. The V16 stores 2-byte intensity values needed for the correction math.

## Step 4: Isovoxel resampling

> **IMPORTANT**: Always ask the user for the target resolution before resampling.
> Different analyses have different requirements:
> - **Layer-dependent / laminar fMRI**: Keep native sub-mm resolution (e.g., 0.7 mm).
> - **Standard group analysis**: 1.0 mm iso is conventional.
> - **Custom**: Match the functional acquisition resolution.

Resample to the chosen isotropic resolution.

```python
# Open the IIHC-corrected VMR
open_bv_document("/path/to/Subj01_UNI_IIHC.vmr")

# Standard: 1.0 mm iso, 256³ cube, sinc interpolation
transform_bv_vmr_to_std_isovoxel(
    out_vmr_iso_filename="/path/to/Subj01_UNI_IIHC_ISO.vmr",
    interpolation_method=3  # 3=sinc (best), 2=cubic, 1=trilinear
)
```

### Custom isovoxel

```python
transform_bv_vmr_to_isovoxel(
    out_vmr_iso_filename="/path/to/Subj01_UNI_IIHC_0.8mm.vmr",
    target_res=0.8,           # 0.8 mm isotropic
    framing_cube_dim=320,     # larger cube for higher resolution
    interpolation_method=3
)
```

### Interpolation method

| Method | Value | Quality | Use case |
|--------|-------|---------|----------|
| Trilinear | 1 | Fast, lower quality | Quick preview |
| Cubic spline | 2 | Good | Standard preprocessing |
| Sinc | 3 | Best, slowest | Final data for analysis |

**Gotcha**: The framing cube MUST be large enough to contain the entire brain at the target resolution. For 1 mm with a typical FOV of 256 mm, use `framing_cube_dim=256`. For 0.8 mm, use 320.

## Step 5: Reorient to standard sagittal (optional)

If data is not in sagittal orientation:

```python
transform_bv_vmr_to_std_sag(
    out_vmr_sag_filename="/path/to/Subj01_UNI_IIHC_ISO_SAG.vmr"
)
```

This reorients to radiological convention (left-is-right on sagittal views).

## Step 6: MNI normalization

Normalize the isovoxel brain to MNI-152 template space.

> **⚠ Sub-millimeter limitation**: BV's `auto_acpc_tal_bv_vmr_transformation`
> and `normalize_bv_vmr_to_mni_space` do NOT work for voxels < 1.0 mm.
> For sub-mm data (e.g., 0.7 mm MP2RAGE for layer-dependent analysis),
> manual AC-PC alignment in BV is required before spatial normalization.
> 1.0 mm iso is the minimum resolution for automatic tools.

```python
# Open the isovoxel VMR
open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")

normalize_bv_vmr_to_mni_space(timeout_seconds=180)

# Output: "Subj01_UNI_IIHC_ISO_MNI.vmr"
```

**Prerequisites**: IIHC (Step 3) must be done first. The brain extraction from IIHC is used to guide template matching.

**Output files created**:
- `*_MNI.vmr` — data in MNI space
- `*_MNI.trf` — transformation file (needed for VTC MNI creation)

## Step 7: AC-PC and Talairach transformation

```python
auto_acpc_tal_bv_vmr_transformation(timeout_seconds=180)
```

This performs:
1. Mid-sagittal plane detection
2. AC and PC point identification
3. Cerebral border detection
4. Transformation to AC-PC and Talairach space

**Output files**:
- `*_ACPC.vmr` — data in AC-PC space
- `*_ACPC.trf` — AC-PC transformation
- `*_TAL.vmr` — data in Talairach space
- `*_TAL.tal` — Talairach landmarks file

## Step 8: Deface

Remove facial features for anonymization:

```python
# On the isovoxel VMR (1 mm required)
open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")
deface_bv_vmr(timeout_seconds=120)
```

**Requirements**: 1 mm iso-voxel data. Works on both native and MNI space VMRs. For MNI space: data must be 256³.

**Alternative — deface at DICOM level** (before VMR creation):

```python
deface_bv_anatomical_dicoms(
    input_directory="/path/to/raw/dicoms",
    output_directory="/path/to/defaced/dicoms",
    timeout_seconds=180
)
```

## Minimal pipeline (for quick coregistration)

```
[1] Create VMR → [3] IIHC → [4] Isovoxel
```

This gives you a brain-extracted, bias-corrected, isovoxel VMR ready for BBR coregistration.

## Full pipeline script

```python
# === Setup ===
base_dir = "/path/to/project"
target_dir = os.path.join(base_dir, "preprocessed")
subj_id = "Subj01"
os.makedirs(target_dir, exist_ok=True)

# === Step 1: Create VMR ===
os.chdir(os.path.join(base_dir, "dicoms"))
vmr_path = create_vmr_from_bv_dicom(
    file_of_series="/path/to/dicoms/Subj01-0005-0001-00001.dcm"
)
vmr_name = f"{subj_id}_UNI.vmr"
save_active_document_as(file_name=os.path.join(target_dir, vmr_name))
close_active_document()

# === Step 2: MP2RAGE (if applicable) ===
run_mp2rage_denoise(
    chosen_factor=10.0,
    path_uni=os.path.join(target_dir, f"{subj_id}_UNI.v16"),
    path_inv1=os.path.join(target_dir, f"{subj_id}_INV1.v16"),
    path_inv2=os.path.join(target_dir, f"{subj_id}_INV2.v16"),
    uniden_filename=f"{subj_id}_uniden.v16",
    save_vmr=True
)

# === Step 3: IIHC ===
open_bv_document(os.path.join(target_dir, f"{subj_id}_UNI.vmr"))
correct_bv_vmr_intensity_inhomogeneities(timeout_seconds=120)
# Now: Subj01_UNI_IIHC.vmr exists
close_active_document()

# === Step 4: Isovoxel ===
open_bv_document(os.path.join(target_dir, f"{subj_id}_UNI_IIHC.vmr"))
transform_bv_vmr_to_std_isovoxel(
    out_vmr_iso_filename=os.path.join(target_dir, f"{subj_id}_UNI_IIHC_ISO.vmr"),
    interpolation_method=3
)
close_active_document()

# === Step 5: MNI ===
open_bv_document(os.path.join(target_dir, f"{subj_id}_UNI_IIHC_ISO.vmr"))
normalize_bv_vmr_to_mni_space(timeout_seconds=180)
# Now: Subj01_UNI_IIHC_ISO_MNI.vmr + .trf
close_active_document()
```

## Gotchas

- **IIHC needs V16**: If IIHC fails with "no V16 data," ensure the V16 file exists alongside the VMR (same basename, `.v16` extension). BV auto-creates it from VMR on first load.
- **MNI normalization failure**: Usually due to poor brain extraction. Re-run IIHC with `include_brain_extraction=True` and check that the brain mask looks correct. For non-human or atypical brains, manual AC-PC alignment may be needed before auto-normalization.
- **Defacing requirements**: 1 mm isotropic, or MNI 256³. If your data doesn't meet this, transform to isovoxel first.
- **Disk space**: Each step creates a new VMR (~17 MB for 256³ uint8, ~34 MB for V16). The full pipeline can consume 200+ MB per subject. Clean up intermediate files if needed.
- **MP2RAGE factor reset**: If you re-run MP2RAGE denoising, the `uniden.v16` file is overwritten. Keep the original UNI/INV1/INV2 files safe.
- **Working directory**: BV may change CWD. Always use absolute paths or `os.chdir()` before each step.
