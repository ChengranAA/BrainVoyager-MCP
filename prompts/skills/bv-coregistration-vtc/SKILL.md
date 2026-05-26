---
name: bv-coregistration-vtc
description: >
  Coregister preprocessed FMR data to anatomical VMR and create VTC files in native,
  MNI, or Talairach space. Covers BBR (boundary-based registration) and intensity-based
  coregistration, VTC creation with full parameter control, VTC-level filtering/smoothing,
  and linking VTCs to MDM group design matrices. Use when the user needs to "coregister
  functional to anatomical," "create VTC," "transform to MNI," "transform to Talairach,"
  "link VTC," or "set up group analysis." Assumes anatomical VMR is preprocessed
  (IIHC + isovoxel) and FMR is preprocessed (slice timing + motion correction).
compatibility: Requires BrainVoyager MCP (fMRI + Anatomy servers). Preprocessed VMR and FMR must exist.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager Coregistration & VTC Creation

Align functional data to anatomy and transform to reference space.

## Workflow

```
Preprocessed FMR + Preprocessed VMR
        │
        ├─ [1] Coregister FMR to VMR   ← BBR (preferred) or intensity-based
        │       Produces: IA.trf, FA.trf
        │
        ├─ [2] Create VTC               ← native / MNI / Tal space
        │       Produces: .vtc file
        │
        ├─ [3] VTC post-processing      ← high-pass filter, spatial smooth
        │
        └─ [4] Link VTC to MDM          ← for group GLM
```

## Prerequisites

1. **Preprocessed FMR**: At minimum, slice-timing + motion-corrected. High-pass filtering and smoothing are optional (can be done at VTC level).
2. **Preprocessed VMR**: IIHC-corrected + isovoxel. MNI/Tal normalization if creating VTC in those spaces.
3. **All files in the same directory** (or use absolute paths).

## Step 1: Coregister FMR to VMR

### Method A: BBR (Boundary-Based Registration) — Recommended

BBR is more accurate, especially for EPI data with distortion. It uses the brain boundary from the VMR segmentation.

```python
# Open the preprocessed VMR (IIHC + isovoxel)
open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")

# Run BBR coregistration
vtc_coregister_fmr_to_vmr_bbr(
    fmr_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    timeout_seconds=300
)
```

**How BBR works**:
1. Initial alignment using DICOM header geometry
2. BV segments the VMR to find the WM/GM boundary
3. Creates a mesh of the boundary (stored as `.srf` file)
4. Iteratively aligns the EPI to maximize intensity gradient at the boundary
5. Produces `*_IA.trf` (initial alignment) and `*_FA.trf` (final alignment)

**The first BBR run is slow** because BV must segment the VMR and create the mesh. Subsequent runs on the same VMR reuse the mesh and are much faster.

### Method B: Intensity-based coregistration

Fallback when BBR mesh creation fails (e.g., poor brain extraction):

```python
open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")

vtc_coregister_fmr_to_vmr(
    fmr_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    iihc_func=False,   # apply IIHC to first functional volume?
    use_attached_amr=0,  # 0=use first vol, 1=use attached AMR
    timeout_seconds=300
)
```

### Coregistering multiple runs

Each run must be coregistered individually:

```python
fmr_files = [
    "Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    "Subj01_Task_run02_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    # ...
]

open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")

for fmr in fmr_files:
    vtc_coregister_fmr_to_vmr_bbr(
        fmr_file=f"/path/to/{fmr}",
        timeout_seconds=300
    )
    print(f"Coregistered: {fmr}")
```

**Output for each run**:
- `*_IA.trf` — initial alignment transformation
- `*_FA.trf` — final alignment transformation
- `*_IA-TO-FA.trf` — combined IA + FA

These `.trf` files are needed for VTC creation.

## Step 2: Create VTC

### VTC in native VMR space

```python
# VMR must be open (the same VMR used for coregistration)
open_bv_document("/path/to/Subj01_UNI_IIHC_ISO.vmr")

vtc_create_in_native_space(
    fmr_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    coreg_ia_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_IA.trf",
    coreg_fa_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_FA.trf",
    vtc_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_NATIVE.vtc",
    res_to_anat=2,                          # 1=same as VMR, 2=double voxel size
    interpolation_method=2,                 # 2=cubic, 1=trilinear, 3=sinc
    bounding_box_intensity_threshold=100,   # separates brain from background
    data_type=2                             # 2=uint16, 3=float32
)
```

### VTC in MNI space

Requires the MNI transformation from anatomical preprocessing:

```python
vtc_create_in_mni_space(
    fmr_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    coreg_ia_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_IA.trf",
    coreg_fa_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_FA.trf",
    mni_trf_file="/path/to/Subj01_UNI_IIHC_ISO_MNI.trf",
    vtc_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_MNI.vtc",
    res_to_anat=1,     # 1=1mm, 2=2mm, 3=3mm isotropic in MNI
    interpolation_method=2,
    bounding_box_intensity_threshold=100,
    data_type=2
)
```

### VTC in Talairach space

Requires both AC-PC transformation and Talairach landmarks:

```python
vtc_create_in_tal_space(
    fmr_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF.fmr",
    coreg_ia_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_IA.trf",
    coreg_fa_trf_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_FA.trf",
    acpc_trf_file="/path/to/Subj01_UNI_IIHC_ISO_ACPC.trf",
    tal_file="/path/to/Subj01_UNI_IIHC_ISO_TAL.tal",
    vtc_file="/path/to/Subj01_Task_run01_M_SCSTBL_3DMCTS_THPGLMF_TAL.vtc",
    res_to_anat=1,
    interpolation_method=2,
    bounding_box_intensity_threshold=100,
    data_type=2
)
```

### VTC parameter guide

#### Resolution (`res_to_anat`)

| Value | Native space | MNI/Tal space |
|-------|-------------|---------------|
| 1 | Same as VMR (e.g., 1 mm) | 1 mm isotropic |
| 2 | Double VMR voxel (e.g., 2 mm) | 2 mm isotropic |
| 3 | Triple VMR voxel (e.g., 3 mm) | 3 mm isotropic |

For standard fMRI (2-3 mm native), use `res_to_anat=1`. For high-res (1 mm), consider `res_to_anat=2` to reduce file size and computation.

#### Interpolation method

| Method | Value | When to use |
|--------|-------|-------------|
| Trilinear | 1 | Fast, VTC creation preview |
| Cubic spline | 2 | Standard — good balance of speed/quality |
| Sinc | 3 | Best quality, final VTC for publication |

#### Bounding box threshold

The intensity threshold determines which voxels are considered "brain" for the VTC bounding box. For IIHC-corrected VMRs:
- **100** is a good default (WM ~150, GM ~100, CSF ~60 in BV uint8)
- Lower (50-80) includes more CSF and edge voxels
- Higher (120-150) restricts to WM-heavy regions

#### Data type

| Type | Value | Range | File size (relative) |
|------|-------|-------|---------------------|
| uint8 | 1 | 0-225 | 1× |
| uint16 | 2 | 0-65535 | 2× |
| float32 | 3 | IEEE float | 4× |

Use `uint16` (2) for standard fMRI. Use `float32` (3) if you need to preserve exact float values (e.g., z-scores, percent signal change).

## Step 3: VTC post-processing

### Link VTC to VMR

After creation, link the VTC to view it in BV:

```python
vtc_link(vtc_file="/path/to/Subj01_Task_run01_MNI.vtc")
```

### Temporal high-pass filtering on VTC

```python
# FFT method (precise frequency control) — preferred for resting-state
vtc_filter_highpass_fft(highpass=0.008, highpass_unit="Hz")

# GLM Fourier (same as FMR level)
vtc_filter_highpass_glm_fourier(n_cycles=3)

# GLM DCT
vtc_filter_highpass_glm_dct(n_basis_functions=2)
```

### Spatial smoothing on VTC

```python
vtc_smooth_spatial(gauss_fwhm=4.0, fwhm_unit="mm")
```

**Smoothing at VTC level is preferred** over FMR-level smoothing because it avoids interpolating already-smoothed data during the coregistration + VTC creation transform chain.

## Step 4: Set up group analysis (MDM)

For group-level GLM, create a Multi-Design Matrix (MDM) file referencing all VTCs:

```python
# MDM files are XML. BV can create them via the GUI, or you can build manually.
# Once created, you can query which VTCs are referenced:

vtc_list = get_vtcs_of_mdm(mdm_file="/path/to/group_design.mdm")
```

## Batch processing (all runs → VTCs)

```python
import os

target_dir = "/path/to/preprocessed"
vmr_path = os.path.join(target_dir, "Subj01_UNI_IIHC_ISO.vmr")
mni_trf = os.path.join(target_dir, "Subj01_UNI_IIHC_ISO_MNI.trf")

# Coregistration
open_bv_document(vmr_path)

fmr_files = [f for f in os.listdir(target_dir) if f.endswith("_THPGLMF.fmr")]

for fmr in fmr_files:
    fmr_full = os.path.join(target_dir, fmr)
    
    # BBR coregistration
    vtc_coregister_fmr_to_vmr_bbr(fmr_file=fmr_full, timeout_seconds=300)
    
    # Derive IA/FA paths (BV uses the FMR basename with _IA.trf, _FA.trf)
    ia_trf = fmr_full.replace('.fmr', '_IA.trf')
    fa_trf = fmr_full.replace('.fmr', '_FA.trf')
    
    # Create VTC in MNI space
    vtc_name = fmr.replace('.fmr', '_MNI.vtc')
    vtc_create_in_mni_space(
        fmr_file=fmr_full,
        coreg_ia_trf_file=ia_trf,
        coreg_fa_trf_file=fa_trf,
        mni_trf_file=mni_trf,
        vtc_file=os.path.join(target_dir, vtc_name),
        res_to_anat=2,
        interpolation_method=2,
        bounding_box_intensity_threshold=100,
        data_type=2
    )
    print(f"Created: {vtc_name}")
    close_active_document()
```

## Gotchas

- **BBR mesh reuse**: The first BBR run on a VMR creates a mesh (`.srf`). If the mesh already exists from a previous run, BV will reuse it. If you change the VMR (e.g., different IIHC), delete the old `.srf` files to force mesh regeneration.
- **TRF file naming**: BV auto-names TRF files based on the FMR basename. For `Subj01_Task_run01_M.fmr`:
  - `Subj01_Task_run01_M_IA.trf`
  - `Subj01_Task_run01_M_FA.trf`
  - `Subj01_Task_run01_M_IA-TO-FA.trf`
- **VMR must stay open**: During VTC creation, the VMR used for coregistration must be the active document. Don't close it between coregistration and VTC creation.
- **Bounding box check**: If VTC creation produces an unreasonably large or small VTC, adjust `bounding_box_intensity_threshold`. Too low = includes skull/background; too high = cuts off brain regions.
- **MNI/Tal trf file path**: The `mni_trf_file` must be the `.trf` file produced by `normalize_bv_vmr_to_mni_space` (same basename as MNI VMR, `.trf` extension). Similarly for `acpc_trf_file`.
- **VTC in native space first**: If you're unsure about coregistration quality, create a VTC in native space first and inspect the alignment in BV's 3D viewer before committing to MNI/Tal space.
- **Transform chain**: Each step accumulates interpolation error. For best quality: coregister (trilinear OK) → VTC creation (sinc) → smoothing (Gaussian). Avoid: FMR smoothing → coregistration → VTC creation.
