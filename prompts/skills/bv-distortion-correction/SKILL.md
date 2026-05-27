---
name: bv-distortion-correction
description: >
  Correct EPI distortions using FSL topup with AP/PA blip-up/blip-down acquisitions.
  Covers FMR→NIfTI conversion, fslmerge, topup estimation, applytopup, and NIfTI→FMR
  conversion back into BrainVoyager. Use when the user needs to "correct distortions,"
  "run topup," "apply topup," "unwarp EPI," "AP/PA correction," or "FSL distortion
  correction." Requires FSL installed and motion-corrected FMRs with short AP and PA
  acquisitions.
compatibility: Requires FSL (topup, applytopup, fslmerge) installed on the system. Python with bvbabel and nibabel. BV MCP (fMRI + Core servers for shell commands).
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager Distortion Correction (FSL topup)

Correct EPI susceptibility distortions using FSL topup with opposite phase-encode (AP/PA) acquisitions.

## Workflow

```
AP FMR (2 vols)  +  PA FMR (2 vols)          Functional FMRs (all runs)
       │                    │                          │
       ├─ [1] FMR→NIfTI ────┤                          │
       ├─ [2] fslmerge ─────┤                          │
       ├─ [3] topup ────────┤                          │
       │                    │                          │
       └─ [4] applytopup ───┴──── [on each run] ───────┤
                                                        │
                                              [5] NIfTI→FMR
                                                        ▼
                                             Distortion-corrected FMRs
```

## Prerequisites

- **FSL must be installed** (`topup`, `applytopup`, `fslmerge` on PATH)
- **AP and PA acquisitions**: Short runs (2-5 volumes) with opposite phase-encoding directions
- **All runs must be motion-corrected** (up to `_3DMCTS.fmr`) BEFORE distortion correction
- **Apply topup BEFORE HPF and BBR** — the corrected FMR flows naturally through BV's
  preprocessing pipeline. NIfTI→FMR round-trip through BV's affine is fragile; avoid re-import.
- **Python packages**: `bvbabel`, `nibabel`, `numpy`

## Step 1: Convert FMR to NIfTI

> **⚠ Mosaic FMR caveat**: `bvbabel.fmr.read_fmr()` fails on mosaic-created FMRs
> because the header has `DimX=DimY=DimZ=0`. Use BV's internal NIfTI export instead:
> `doc.save_as('output.nii')` via `exec_bv_python`. This produces proper affine and data.

Motion-corrected FMRs must be converted to NIfTI for FSL.

```python
import os
import numpy as np
import nibabel as nb
import bvbabel

def fmr_to_nifti(fmr_path, output_dir=None):
    """Convert a BV FMR/STC to NIfTI."""
    if output_dir is None:
        output_dir = os.path.dirname(fmr_path)
    
    # Read the STC data
    header, data = bvbabel.fmr.read_fmr(fmr_path)
    
    # Rearrange axes for FSL (BV uses different axis order)
    # data shape: [volumes, x, y, slices] -> [x, y, slices, volumes]
    
    basename = fmr_path.replace('.fmr', '')
    outname = os.path.join(output_dir, os.path.basename(basename) + '.nii.gz')
    
    img = nb.Nifti1Image(data, affine=np.eye(4))
    nb.save(img, outname)
    return outname

# Convert AP and PA
ap_nii = fmr_to_nifti("/path/to/Pilot_LetterImagery_AP_SCSTBL_3DMCTS.fmr")
pa_nii = fmr_to_nifti("/path/to/Pilot_LetterImagery_PA_SCSTBL_3DMCTS.fmr")

# Convert all functional runs
run_niis = []
for fmr in fmr_filenames:
    run_niis.append(fmr_to_nifti(f"/path/to/{fmr}"))
```

**Gotcha**: FMR data from bvbabel may need axis rearrangement. Check the shape — BV stores data as `[volumes, dim_x, dim_y, slices]`. bvbabel's `read_fmr` with `rearrange_data_axes=True` handles this.

## Step 2: Merge AP and PA with fslmerge

```bash
fslmerge -t Pilot_APPA.nii.gz Pilot_LetterImagery_AP_SCSTBL_3DMCTS.nii.gz Pilot_LetterImagery_PA_SCSTBL_3DMCTS.nii.gz
```

Run via `run_bv_shell_command`:

```python
run_bv_shell_command(
    shell_command="fslmerge -t /path/to/Pilot_APPA.nii.gz /path/to/Pilot_AP.nii.gz /path/to/Pilot_PA.nii.gz",
    timeout_seconds=30
)
```

## Step 3: Create acquisition parameters file

FSL needs a file describing phase encoding. For AP/PA with 2 volumes each:

```python
# Create acqparams.txt
# AP encoding:  [0  1  0  echo_spacing]
# PA encoding:  [0 -1  0  echo_spacing]
# echo_spacing is in seconds (typical: 0.05 for 50ms)

ap_line = "0 1 0 0.05\n"
pa_line = "0 -1 0 0.05\n"

with open("/path/to/acqparams.txt", "w") as f:
    f.write(ap_line * 2)  # 2 AP volumes
    f.write(pa_line * 2)  # 2 PA volumes
```

**The 4th column is the total readout time in seconds**, in the range 0.01–0.2s.
Topup will reject values outside this range. For 0.8mm mb2 EPI w/ GRAPPA3, ~0.03s is typical.

### Gotchas

- **bvbabel fails on mosaic FMRs**: `create_mosaic_fmr` leaves DimX/DimY/DimZ=0 in the header.
  Use BV's `doc.save_as('.nii')` instead of bvbabel for NIfTI conversion.
- **fslmerge can't handle BV NIfTI**: Orientation inconsistency. Use Python nibabel to
  concatenate along axis 3: `np.concatenate([ap, pa], axis=3)`.
- **Reverse-PE scans share noise trim**: Same protocol = same noise volumes. If main run
  trims N from end, reverse-PE scans trim N too (even though they're only 5v).
- **Set FSLOUTPUTTYPE**: `export FSLOUTPUTTYPE=NIFTI_GZ` before running FSL tools.
- **Topup timeout**: Topup can take minutes on large volumes. Submit and wait.
- **Keep original BV NIfTI affines**: Use the affine from the first file when merging.

## Step 5: Convert corrected NIfTI back to FMR

After `applytopup`, convert the corrected NIfTI back to BV FMR/STC format:

```python
import numpy as np, nibabel as nb, shutil

cd = '/path/to/preprocessed'
corr = nb.load(cd+'/run_corrected.nii.gz').get_fdata()
# NIfTI [X, Y, Z, T] → BV STC [T, Z, Y, X] in C order
stc_data = np.transpose(corr, (3, 2, 1, 0)).astype(np.float32).copy()
stc_data.tofile(cd+'/run_corrected.stc')

# Clone FMR header — append topup suffix, don't strip preprocessing suffixes
src_fmr = cd+'/run_THPGLMF3c.fmr'      # original after HPF
dst_fmr = cd+'/run_THPGLMF3c_TOPPED.fmr'  # append _TOPPED
shutil.copy(src_fmr, dst_fmr)

# Update Prefix field (BV derives STC name from this)
with open(dst_fmr) as f: content = f.read()
# Replace ALL occurrences of the old prefix with the new one
content = content.replace('run_THPGLMF3c', 'run_THPGLMF3c_TOPPED')
with open(dst_fmr, 'w') as f: f.write(content)
```

**CRITICAL**:
- **Append suffix, don't strip**: Use `_THPGLMF3c_TOPPED`, not `_corrected`.
  Existing preprocessing suffixes tell you what's been applied.
- **Update ALL prefix occurrences** in the FMR header — the `Prefix` field,
  any STC references, and the filename itself.
- **STC order**: BV stores `[T, Z, Y, X]` with X fast-varying in C order.
  NIfTI is `[X, Y, Z, T]` → transpose to `(3,2,1,0)`.

For LR/RL encoding instead of AP/PA:

```python
lr_line = "1 0 0 0.05\n"
rl_line = "-1 0 0 0.05\n"
```

## Step 4: Create b02b0.cnf config file

FSL topup needs a configuration file. Use the standard `b02b0.cnf`:

```python
b0cnf = """# Resolution (knot-spacing) of warps in mm
--warpres=20,16,14,12,10,6,4,4,4
# Subsampling level
--subsamp=2,2,2,2,2,1,1,1,1
# FWHM of gaussian smoothing
--fwhm=8,6,4,3,3,2,1,0,0
# Maximum number of iterations
--miter=5,5,5,5,5,10,10,20,50
# Relative weight of regularisation
--lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001
# If set to 1 lambda is multiplied by the current average squared difference
--ssqlambda=1
# Regularisation model
--regmod=bending_energy
# If set to 1 movements are estimated along with the field
--estmov=0,0,0,0,0,0,0,0,0
# 0=Levenberg-Marquardt, 1=Scaled Conjugate Gradient
--minmet=0,0,0,0,0,1,1,1,1
# Quadratic or cubic splines
--splineorder=3
# Precision for calculation and storage of Hessian
--numprec=double
# Linear or spline interpolation
--interp=spline
# If set to 1 the images are individually scaled to a common mean
--scale=1"""

with open("/path/to/b02b0.cnf", "w") as f:
    f.write(b0cnf)
```

## Step 5: Run topup

```bash
topup --imain=Pilot_APPA.nii.gz \
      --datain=acqparams.txt \
      --config=b02b0.cnf \
      --out=Pilot_APPA_topup
```

Via `run_bv_shell_command`:

```python
run_bv_shell_command(
    shell_command="cd /path/to/preprocessed && topup --imain=Pilot_APPA.nii.gz --datain=acqparams.txt --config=b02b0.cnf --out=Pilot_APPA_topup",
    timeout_seconds=300
)
```

This produces:
- `Pilot_APPA_topup_fieldcoef.nii.gz` — the field coefficients
- `Pilot_APPA_topup_movpar.txt` — movement parameters

## Step 6: Apply topup to each run

```bash
applytopup -i Pilot_run01_M_SCSTBL_3DMCTS.nii.gz \
           -a acqparams.txt \
           -t Pilot_APPA_topup \
           -x 1 -m jac -v \
           -o Pilot_run01_M_SCSTBL_3DMCTS_topup
```

For each functional run:

```python
for nii_file in run_nii_filenames:
    basename = os.path.basename(nii_file).replace('.nii.gz', '')
    cmd = (
        f"cd /path/to/preprocessed && "
        f"applytopup -i {basename}.nii.gz "
        f"-a acqparams.txt "
        f"-t Pilot_APPA_topup "
        f"-x 1 -m jac -v "
        f"-o {basename}_topup"
    )
    run_bv_shell_command(shell_command=cmd, timeout_seconds=120)
```

**Flags explained**:
- `-x 1`: Use spline interpolation
- `-m jac`: Apply Jacobian modulation (corrects intensity)
- `-v`: Verbose output

## Step 7: Convert corrected NIfTI back to FMR

```python
def nifti_to_fmr(nifti_path, reference_fmr_path, output_dir=None):
    """Convert a NIfTI back to BV FMR format using a reference FMR header."""
    if output_dir is None:
        output_dir = os.path.dirname(nifti_path)
    
    # Load NIfTI data
    nii_data = nb.load(nifti_path).get_fdata()
    
    # Load reference FMR header
    fmr_header, _ = bvbabel.fmr.read_fmr(reference_fmr_path)
    
    # Write new STC
    basename = os.path.basename(nifti_path).replace('.nii.gz', '')
    new_stc = os.path.join(output_dir, basename + '.stc')
    bvbabel.stc.write_stc(new_stc, nii_data, data_type=fmr_header["DataType"])
    
    # Create new FMR by copying the reference and replacing the STC reference
    new_fmr = os.path.join(output_dir, basename + '.fmr')
    ref_data = open(reference_fmr_path, 'r').read()
    ref_basename = os.path.basename(reference_fmr_path).replace('.fmr', '')
    ref_data = ref_data.replace(ref_basename, basename)
    
    with open(new_fmr, 'w') as f:
        f.write(ref_data)
    
    return new_fmr

# Convert each topup-corrected NIfTI back to FMR
for nii_file, ref_fmr in zip(topup_nii_files, original_fmr_files):
    new_fmr = nifti_to_fmr(nii_file, ref_fmr, target_dir)
    print(f"Created: {new_fmr}")
```

## Step 8: Continue preprocessing

After distortion correction, run temporal high-pass filtering on the corrected FMRs. Then proceed to coregistration and VTC creation.

## Full shell workflow (alternative)

If using FSL directly on the command line (all commands via `run_bv_shell_command`):

```python
target_dir = "/path/to/preprocessed"

# 1. Merge AP/PA
run_bv_shell_command(
    f"cd {target_dir} && fslmerge -t Pilot_APPA.nii.gz Pilot_AP.nii.gz Pilot_PA.nii.gz",
    timeout_seconds=30
)

# 2. Run topup
run_bv_shell_command(
    f"cd {target_dir} && topup --imain=Pilot_APPA.nii.gz --datain=acqparams.txt --config=b02b0.cnf --out=Pilot_APPA_topup",
    timeout_seconds=300
)

# 3. Apply to each run
for nii in run_niis:
    basename = os.path.basename(nii).replace('.nii.gz', '')
    run_bv_shell_command(
        f"cd {target_dir} && applytopup -i {basename}.nii.gz -a acqparams.txt -t Pilot_APPA_topup -x 1 -m jac -o {basename}_topup",
        timeout_seconds=120
    )
```

## Gotchas

- **Echo spacing**: The 4th column in `acqparams.txt` is echo spacing (dwell time), NOT total readout time. For typical Siemens 3T EPI with GRAPPA 2: ~0.5 ms = 0.0005 s. The example pipeline uses 0.05 — this is unusually large and may reflect total readout time. Verify from DICOM tag (0019,1028) or BIDS JSON.
- **Number of volumes in acqparams.txt**: MUST match the number of volumes in the merged APPA file. If you have 2 AP + 2 PA = 4 volumes, acqparams.txt MUST have 4 lines.
- **AP = PA encoding direction**: "AP" means Anterior→Posterior phase encoding (blip-down), which should use `0 1 0` (positive Y). "PA" is `0 -1 0` (negative Y). These may be reversed depending on your scanner convention. Check the DICOM header tag (0018,1312) for InPlanePhaseEncodingDirection.
- **Jacobian modulation**: The `-m jac` flag is important — it corrects for intensity compression/stretching in the unwarped image. Without it, subsequent analysis may find spurious activations near distorted regions.
- **FMR→NIfTI axis ordering**: BV STC data from bvbabel may need `rearrange_data_axes=True` or manual transposition. Always verify shapes: `nii.shape` should be `[X, Y, Slices, Volumes]`.
- **Which runs to distortion-correct**: Apply topup to ALL functional runs (including task runs, resting state, field maps for other purposes). The AP/PA pair is only used for field estimation.
- **Out-of-memory on large datasets**: Apply topup to each run separately rather than trying to process all runs at once.
