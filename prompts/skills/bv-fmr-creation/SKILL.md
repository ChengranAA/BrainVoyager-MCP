---
name: bv-fmr-creation
description: >
  Create BrainVoyager FMR documents from functional DICOM series (Siemens mosaic,
  single-image, or multi-frame enhanced DICOM). Covers naming conventions, BIDS NIfTI
  export, AP/PA extraction for distortion correction, and raw mosaic FMR creation.
  Use when the user needs to "create FMR," "import functional DICOM," "convert DICOM
  to FMR," or "set up functional runs in BV." Assumes DICOMs are already renamed.
compatibility: Requires BrainVoyager MCP (fMRI server). DICOM data must be renamed.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager FMR Creation

Create FMR (Functional MR) documents from DICOM series.

## Preferred method: `create_fmr_from_bv_dicom`

This is the best tool for modern DICOM data. It auto-detects all parameters from the DICOM header — no need to manually specify mosaic dimensions, slice count, or endianness.

```
create_fmr_from_bv_dicom(
    file_of_series="/path/to/dicoms/Subj01-0010-0001-00001.dcm",
    fmr_stc_filename="subj01_task_run1",
    target_folder="/path/to/output",
    protocol_file=""              # optional .prt for slice timing
)
```

**Only one DICOM file is needed** — BV reads the entire series from the header. Returns the path to the created `.fmr` file.

**Supports**: single-image DICOM, Siemens mosaic, multi-frame enhanced DICOM.

## Naming conventions

Follow this pattern for consistency — downstream tools chain filenames:

```
{subject_id}_{condition}_{run}_{signal}[_suffix]
```

| Component | Example | Source |
|-----------|---------|--------|
| subject_id | `Pilot`, `Subj07` | User-defined or PatientName |
| condition | `LetterImagery`, `MemPat` | Task name |
| run | `run01`, `Img01` | From SeriesDescription |
| signal | `M` (magnitude), `P` (phase), `ND` | ImageType[2] |
| suffix | `AP`, `PA`, `nordic` | Optional |

Examples:
- `Pilot_LetterImagery_run01_M`
- `Subj07_MemPat_run02_M_nordic`

## Alternative: Raw mosaic FMR creation

If you need fine control over mosaic parameters (older Siemens data), use `create_fmr_from_bv_mosaic`:

```
create_fmr_from_bv_mosaic(
    first_file="/path/to/dicoms/first_volume.dcm",
    n_volumes=240,
    n_slices=72,
    fmr_stc_filename="subj01_task_run1",
    target_folder="/path/to/output",
    skip_n_volumes=0,
    first_volume_amr=False,
    big_endian=False,
    mosaic_rows=64,        # from ds.Rows
    mosaic_cols=64,        # from ds.Columns
    slice_rows=104,        # from ds.AcquisitionMatrix
    slice_cols=104,        # from ds.AcquisitionMatrix
    bytes_per_pixel=2
)
```

**When to use this vs `create_fmr_from_bv_dicom`**: Only when you need to override DICOM header values (e.g., custom mosaic dimensions, skipping initial volumes within the creation step).

## BIDS NIfTI export

To create BIDS-compliant NIfTI directly from DICOM:

```
create_fmr_nifti_bids_from_bv_dicom(
    file_of_series="/path/to/dicoms/Subj01-0010-0001-00001.dcm",
    subj_id=7,
    ses_id=1,
    run_id=1,
    task_name="rest",
    project_folder="/path/to/bids_project",
    protocol_file=""
)
```

This produces `sub-07_ses-01_task-rest_run-01_bold.nii.gz` in the BIDS structure.

## AP/PA extraction for distortion correction

For FSL topup, you need short AP and PA acquisitions. Extract the first few volumes from the appropriate series:

```python
# AP: create with first 2-5 volumes
create_fmr_from_bv_dicom(
    file_of_series=ap_dicom_file,
    fmr_stc_filename="Pilot_LetterImagery_AP",
    target_folder=target_folder
)
# Then open the FMR and manually trim volumes in BV, or use skip_n_volumes

# PA: same approach but from the opposite phase-encode series
create_fmr_from_bv_dicom(
    file_of_series=pa_dicom_file,
    fmr_stc_filename="Pilot_LetterImagery_PA",
    target_folder=target_folder
)
```

**Important**: The AP and PA FMRs should have the SAME number of volumes (typically 2-5). After slice timing and motion correction on these short runs, they feed into `fslmerge` for topup.

## Batch creation from project dictionary

Given a project dictionary from `bv-dicom-setup`:

```python
import os

for filename, info in project_dict.items():
    fmr_stc_filename = "_".join([
        info['subject_id'],
        info['condition'],
        info['run'],
        info['signal']
    ])
    
    # BV may change CWD — always chdir to DICOM dir first
    os.chdir(dicom_directory)
    
    fmr_path = create_fmr_from_bv_dicom(
        file_of_series=os.path.join(dicom_directory, filename),
        fmr_stc_filename=fmr_stc_filename,
        target_folder=target_folder
    )
    print(f"Created: {fmr_path}")
```

## Gotchas

- **BV changes working directory**: Always `os.chdir(data_dir)` before calling creation tools. BV may reset CWD to its install path.
- **DICOM must be renamed first**: `create_fmr_from_bv_dicom` expects standard BV naming (`PatientName-SeriesNumber-VolumeNumber-ImageNumber.dcm`). Run `bv-dicom-setup` first.
- **Close FMR documents after creation**: The returned document object stays open. Call `.close()` or use `close_active_document` to free memory before creating the next one. 
- **NIfTI creation needs bvbabel + nibabel**: If converting FMR→NIfTI manually (for FSL), use `bvbabel.fmr.read_fmr()` and `nibabel.Nifti1Image`. See `bv-distortion-correction` skill.
- **Mosaic dimension mismatch**: If `slice_rows`/`slice_cols` are 0 in the DICOM header, try `AcquisitionMatrix[1]` and `AcquisitionMatrix[2]` as fallback.
- **Skipping end volumes**: BV doesn't directly support "skip last N volumes" during creation. Create the full FMR, then trim during preprocessing or use the FMR's volume range settings.
