---
name: bv-fmri-preprocessing
description: >
  Standard fMRI preprocessing in BrainVoyager: slice timing correction, 3D motion
  correction, temporal high-pass filtering (GLM Fourier/DCT), and spatial smoothing.
  Covers both FMR-level and VTC-level operations. Use when the user needs to
  "preprocess fMRI data," "correct slice timing," "motion correct," "high-pass filter,"
  "spatially smooth," or "prepare data for GLM analysis." Assumes FMRs are already
  created (see bv-fmr-creation).
compatibility: Requires BrainVoyager MCP (fMRI server). FMR documents must exist in target folder.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager fMRI Preprocessing

Preprocess functional data: slice timing → motion correction → temporal filtering → spatial smoothing.

## Pipeline order (MUST follow this sequence)

> **⚠ Always ask the user**: How many noise volumes to skip (usually at the END)?
> Keep noise volumes → degrade motion correction & slice timing.
> Skip them: reduce `n_volumes` at FMR creation (BV skip handles start only).
> Or: externally denoise with NORDIC then keep all.

```
FMR (raw STC)
  │
  ├─ [1] Slice Timing Correction   ← correct_slicetiming_using_timingtable
  ├─ [2] Motion Correction         ← 3D rigid-body to first volume
  ├─ [3] Temporal High-Pass Filter ← remove drift (GLM Fourier/DCT)
  └─ [4] Spatial Smoothing         ← 3D Gaussian (FWHM in mm)
  ▼
FMR (preprocessed) → ready for coregistration / VTC creation
```

**Each step modifies the STC data in-place** and produces a new preprocessed FMR file with a suffix appended.

## Step 1: Slice timing correction

**Always run this FIRST**, before motion correction. Use the DICOM timing table method — it handles single-band and multi-band data correctly without needing manual slice order.

```python
# Open the FMR
fmr_doc = open_bv_document("/path/to/subj_task_run_M.fmr")

# Sinc interpolation = 3 (best quality); cubic spline = 2; trilinear = 1
fmr_correct_slice_timing(interpolation_method=3)

# The corrected file is at fmr_doc.preprocessed_fmr_name
# e.g., "subj_task_run_M_SCSTBL.fmr"
```

**Interpolation methods**: 1=trilinear (fastest, lowest quality), 2=cubic spline, 3=sinc (slowest, best quality). Sinc is recommended for high-resolution data.

**Gotcha**: This only works for DICOM-created FMRs (the timing table comes from the DICOM header). If your FMR was created from raw files without DICOM headers, use BV's manual slice timing with an explicit slice order.

## Step 2: Motion correction

3D rigid-body alignment (6 parameters: 3 translation, 3 rotation). Align all volumes to the first volume.

```python
# Open the slice-timing-corrected FMR (close previous first)
fmr_doc = open_bv_document("/path/to/subj_task_run_M_SCSTBL.fmr")

# Standard: trilinear + sinc, full dataset, 100 iterations
fmr_correct_motion(timeout_seconds=300)

# The corrected file: "subj_task_run_M_SCSTBL_3DMCTS.fmr"
```

### Motion correction options

| Tool | Use case |
|------|----------|
| `fmr_correct_motion` | Standard: aligns to volume 1 with trilinear-sinc |
| `fmr_correct_motion_to_vol(target_vol_idx=N)` | Align to a specific volume (e.g., for multi-run alignment) |

### Checking motion parameters

Motion parameters are logged to a `.log` file. Parse it to review:

```python
# The log file is in the same folder as the FMR
# Format: each line contains dx, dy, dz (mm) and rx, ry, rz (degrees)
# Use exec_bv_python to parse and plot
```

**When to align all runs to a common target**: If all runs should be in the same space, motion-correct all runs to the first volume of the FIRST run (use `fmr_correct_motion_to_vol`). This is important for multi-run GLM where runs share a common reference.

## Step 3: Temporal high-pass filtering

Remove low-frequency drift (scanner drift, physiological noise). Run on the motion-corrected FMR.

```python
fmr_doc = open_bv_document("/path/to/subj_task_run_M_SCSTBL_3DMCTS.fmr")

# Option A: GLM Fourier (sine/cosine basis functions)
fmr_filter_highpass_glm_fourier(n_cycles=3)
# Removes 3 cycles of the lowest frequencies

# Option B: GLM DCT (discrete cosine transform)
fmr_filter_highpass_glm_dct(n_basis_functions=2)
# Removes 2 DCT basis functions

# Output: "subj_task_run_M_SCSTBL_3DMCTS_THPGLMF.fmr" (Fourier)
# Output: "subj_task_run_M_SCSTBL_3DMCTS_THPGLMD.fmr" (DCT)
```

### Choosing n_cycles / n_basis_functions

- **Typical values**: 2-3 cycles for Fourier, 2 for DCT
- **Rule of thumb**: The high-pass cutoff ≈ n_cycles × (1 / total_duration)
  - 3 cycles on a 10-min run (600 s) ≈ 0.005 Hz ≈ 200 s cutoff
- **For event-related designs**: 2 cycles is usually sufficient
- **For resting-state**: consider 0.008 Hz (≈ 125 s), use the FFT-based method on VTC instead

**Alternative for resting-state**: Use `vtc_filter_highpass_fft(highpass=0.008, highpass_unit="Hz")` after VTC creation — this gives precise frequency control.

## Step 4: Spatial smoothing

3D Gaussian kernel. Apply to the filtered FMR.

```python
fmr_doc = open_bv_document("/path/to/subj_task_run_M_SCSTBL_3DMCTS_THPGLMF.fmr")

# Typical: 4 mm FWHM
fmr_smooth_spatial(gauss_fwhm=4.0, fwhm_unit="mm")

# Output: "subj_task_run_M_SCSTBL_3DMCTS_THPGLMF_SD3DSS.fmr"
```

### Smoothing guidelines

| FWHM | Use case |
|------|----------|
| 2-3 mm | High-resolution (e.g., 1 mm iso), laminar fMRI |
| 4 mm | Standard resolution (2-3 mm voxels) |
| 6-8 mm | Low SNR, group-level, or when matching legacy processing |

**When to smooth at VTC level instead**: If creating a VTC at lower resolution than the FMR, it's often better to smooth the VTC with `vtc_smooth_spatial`. This avoids interpolating already-smoothed data.

## Full batch preprocessing

Chain all steps for multiple runs:

```python
import os

fmr_files = [
    "Pilot_LetterImagery_run01_M.fmr",
    "Pilot_LetterImagery_run02_M.fmr",
    # ...
]
target_dir = "/path/to/preprocessed"

for fmr_file in fmr_files:
    full_path = os.path.join(target_dir, fmr_file)
    
    # Step 1: Slice timing
    doc = open_bv_document(full_path)
    fmr_correct_slice_timing(interpolation_method=3)
    stc_file = doc.file_name  # or .preprocessed_fmr_name
    close_active_document()
    
    # Step 2: Motion correction
    doc = open_bv_document(stc_file)
    fmr_correct_motion(timeout_seconds=300)
    mc_file = doc.file_name
    close_active_document()
    
    # Step 3: High-pass filter
    doc = open_bv_document(mc_file)
    fmr_filter_highpass_glm_fourier(n_cycles=3)
    hpf_file = doc.file_name
    close_active_document()
    
    print(f"Preprocessed: {hpf_file}")
```

## Temporal smoothing (optional)

Gaussian temporal smoothing is sometimes applied for resting-state or event-related averaging:

```python
fmr_smooth_temporal(gauss_fwhm=2.0, fwhm_unit="data_points")
```

**Rarely used** in standard GLM pipelines — temporal filtering (Step 3) is usually sufficient.

## Gotchas

- **Order matters**: Slice timing MUST come before motion correction. Motion correction assumes all slices were acquired simultaneously; slice timing corrects for staggered acquisition.
- **Close documents between steps**: Each preprocessing step creates a new file and the old document stays open. Call `close_active_document()` between steps to avoid memory accumulation.
- **Filename chain**: BV appends suffixes: `SCSTBL` (slice timing), `3DMCTS` (motion correction), `THPGLMF` (high-pass Fourier), `SD3DSS` (spatial smoothing). Don't rename intermediate files — downstream steps rely on the chain.
- **Long timeouts**: Motion correction on large datasets (e.g., 500+ volumes, high-res) can take minutes. Increase `timeout_seconds` accordingly (default 120 s).
- **Wait for user for long ops**: For large datasets where motion correction takes 5-15+ minutes, submit with a short timeout (~30s), then WAIT for the user to confirm completion before proceeding. BV continues in the background — never retry.
- **STC vs FMR**: Slice timing and motion correction modify the `.stc` data file, and the `.fmr` file is updated to point to the new `.stc`. Both files must stay in the same directory.
- **Multi-band data**: `correct_slicetiming_using_timingtable` automatically handles multi-band/simultaneous multi-slice (SMS) data. Do NOT specify a manual slice order.
