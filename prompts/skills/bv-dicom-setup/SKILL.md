---
name: bv-dicom-setup
description: >
  Rename, anonymize, and discover DICOM datasets for BrainVoyager fMRI preprocessing.
  Use when the user needs to organize raw DICOM directories, standardize file names,
  anonymize patient data, or auto-discover functional and anatomical series to build
  project dictionaries for batch processing. Triggers on mentions of "DICOM setup,"
  "rename DICOMs," "anonymize DICOMs," "scan DICOM directory," or "organize raw data."
compatibility: Requires BrainVoyager MCP (Core server). Python with pydicom for DICOM header parsing.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager DICOM Setup

Rename, anonymize, and discover DICOM data — the prerequisite for all downstream BV pipelines.

## Workflow overview

```
Raw DICOMs  →  [1. Rename]  →  [2. Anonymize]  →  [3. Discover series]  →  Project dicts
```

## Step 1: Rename DICOMs to standard BV format

BV expects DICOM filenames in the pattern `PatientName-SeriesNumber-VolumeNumber-ImageNumber.dcm`.

Use `rename_bv_dicoms` on the raw DICOM directory. This reads DICOM header tags (0010,0010), (0020,0011), (0020,0012), (0020,0013) and renames accordingly.

```
rename_bv_dicoms(directory="/path/to/raw/dicoms")
```

If the patient name should also be replaced for anonymization, use `anonymize_bv_dicoms` instead, which both renames AND replaces the patient name:

```
anonymize_bv_dicoms(directory="/path/to/raw/dicoms", anonymized_patient_name="Subj01")
```

**Gotcha**: These tools rename files in-place and modify DICOM header tag (0010,0010) for anonymize. Work on a copy of the raw data if you need to preserve originals.

## Step 2: Discover all series — present a complete inventory

> **⚠ ALWAYS present the user with a FULL DICOM inventory first.** DICOM series
> can be messy: runs may be unnamed, descriptions may not match expectations,
> SE pairs can be shared or per-run, and unexpected acquisitions (e.g., retinotopy)
> may hide under generic names. Present the complete list and let the user
> classify the data before processing anything.

> **Also ask the user**: _What analysis are you planning?_ (standard GLM, layer-
> dependent, retinotopy/pRF, resting-state). This determines resolution choices,
> noise-volume handling, and whether distortion correction is needed.

Run a discovery script in `exec_bv_python` or `run_bv_shell_command` that prints
for each series: filename, file count, ImageType[2], SeriesDescription.

BV's internal classifier labels **`DWI / FUNC`** = short reverse-PE acquisitions
(typically 5 vols, for topup) and **`FUNC / DWI`** = main functional runs (many
vols). Use this to auto-categorize, but always confirm with the user.

After renaming, you need to identify which DICOMs belong to which functional runs. This requires parsing DICOM headers with `pydicom`. Use `run_bv_shell_command` or `exec_bv_python` to run a discovery script.

### Key DICOM tags for discovery

| Tag | Meaning |
|-----|---------|
| (0010,0010) | Patient name |
| (0020,0011) | Series number |
| (0020,0012) | Acquisition (volume) number |
| (0020,0013) | Instance (image) number |
| (0008,103E) | Series description |
| (0008,0008) | Image type (e.g., `['ORIGINAL', 'PRIMARY', 'M', 'ND']`) |
| (0019,100A) | Number of slices (Siemens) |

### Discovery logic

1. List all files matching `{prefix}-{series}-0001-00001.dcm` (first volume, first slice)
2. For each, read with `pydicom.dcmread()`
3. A file is a **functional run** if:
   - `SeriesDescription` contains "Run" (case-insensitive)
   - `SeriesDescription` does NOT contain "SBRef"
   - Number of volumes > 40 (or a user-specified threshold)
   - If not using NORDIC: skip where `ImageType[2] == 'P'` (phase images)
4. Extract: `run` name from SeriesDescription, signal type from `ImageType[2]`

### Example discovery script

```python
import os, json, pydicom
from glob import glob

data_dir = "/path/to/dicoms"
prefix = os.path.basename(glob(data_dir + '/*')[0]).split('-')[-4]
suffix = '-0001-00001.dcm'
v1i1 = [f for f in os.listdir(data_dir) if prefix in f and suffix in f]

project_dict = {}
for filename in sorted(v1i1):
    ds = pydicom.dcmread(os.path.join(data_dir, filename))
    n_vols = len(glob(f'{data_dir}/{prefix}-{str(ds.SeriesNumber).zfill(4)}*.dcm'))
    
    if ('Run' in ds.SeriesDescription and 
        'SBRef' not in ds.SeriesDescription and 
        n_vols > 40):
        
        if ds.ImageType[2] == 'P':
            continue  # skip phase images
            
        run = ds.SeriesDescription.split('_')[-1]
        if not ('run' in run.lower()):
            run = 'run' + run
            
        project_dict[filename] = {
            'run': run,
            'condition': 'TaskName',  # set by user
            'signal': ds.ImageType[2],
            'subject_id': ds.PatientName,
            'filename': filename,
            'n_volumes': n_vols,
            'seriesDescription': ds.SeriesDescription
        }

# Save for later use
with open('fmr_info.json', 'w') as f:
    json.dump(project_dict, f)
```

## Step 3: Discover anatomical series (build VMR project dictionary)

Similar logic for anatomical scans:

```python
project_dict = {}
for filename in sorted(v1i1):
    ds = pydicom.dcmread(os.path.join(data_dir, filename))
    
    contrast = None
    if 'INV' in ds.SeriesDescription and 'PHS' not in ds.SeriesDescription:
        contrast = ds.SeriesDescription.split('_')[-1]
    elif 'T1_Images' in ds.SeriesDescription:
        contrast = 'T1'
    elif 'UNI_Images' in ds.SeriesDescription:
        contrast = 'UNI'
    
    if contrast:
        project_dict[filename] = {
            'contrast_img': contrast,
            'subject_id': ds.PatientName,
            'filename': filename
        }
```

## Gotchas

- **BV changes working directory**: Always `os.chdir(data_dir)` before DICOM operations. BV may reset CWD to its install path.
- **DICOM filenames before renaming**: Raw DICOM filenames vary by scanner. Always rename first.
- **Post-rename whitespace cleanup**: When anonymized name is shorter than original, BV pads filenames with spaces (e.g., `Subj01                      -0001-...dcm`). Always run: `for f in *.dcm; do mv "$f" "$(echo $f | sed 's/NEWNAME[[:space:]]*/NEWNAME/g')"; done`
- **Mosaic vs single-image DICOM**: Siemens mosaics use tags (0028,0010)=(0028,0011)=mosaic size, while actual slice dims are in AcquisitionMatrix. The `create_fmr_from_bv_dicom` tool handles this automatically.
- **Phase images**: ImageType[2]='P' are phase images from phased-array coils. Skip them unless specifically needed.
- **Large DICOM directories**: Do NOT list all files—use glob patterns. Count files instead with len(glob(...)).
