---
name: bv-file-formats
description: >
  Complete reference for all BrainVoyager file formats — binary structures, field
  specifications, axis conventions, and bvbabel read/write patterns. Covers VMR,
  V16, FMR/STC, VTC, TRF, PRT, SDM, MDM, GLM, VMP, SMP, SRF, MSK, MTC, GTC, POI,
  VOI, SSM, DMR/DWI. Use when the user needs to "read/write BV files," "understand
  file format fields," "convert between formats," "parse headers," "debug file I/O,"
  "use bvbabel," or "inspect binary data." Activate alongside pipeline skills
  (bv-dicom-setup, bv-fmri-preprocessing, etc.) whenever file-level operations are
  needed.
compatibility: Requires Python 3 with bvbabel and NumPy. Also references BV MCP tools.
metadata:
  author: bv-mcp
  version: "1.0"
---

# BrainVoyager File Format Reference

This skill provides the authoritative field-level specification for every BrainVoyager file format, derived from the bvbabel library and BV Developer Guide. Use it to understand binary structures, parse headers, write files programmatically, or debug I/O issues.

## Format categories

| Category | Formats | Storage |
|----------|---------|---------|
| **Text-based** (key:value) | FMR, TRF, PRT, SDM, MDM, POI | ASCII, line-delimited |
| **Binary** (struct-packed) | VMR, V16, VTC, VMP, SMP, GLM, SRF, MSK, MTC, GTC, SSM, VOI, STC, DMR, DWI | Little-endian (`<`) |
| **Hybrid** | FMR (text header + STC binary data) | FMR is text, STC is binary |

## Axis conventions

BrainVoyager uses an **internal LIP+** coordinate system that differs from both Talairach and NIfTI/RAS+:

| Axis | BV internal | Talairach | NIfTI (RAS+) |
|------|-------------|-----------|--------------|
| X (front→back) | Axis 2 after reshape | Y | A→P |
| Y (top→bottom) | Axis 1 after reshape | Z | S→I |
| Z (left→right) | Axis 0 after reshape | X | R→L |

**bvbabel convention**: All `read_*` functions accept `rearrange_data_axes=True` (default), which transposes and flips data to approximate NIfTI RAS+ orientation. `write_*` functions reverse this. When using raw values, you must handle the LIP+↔RAS+ conversion yourself.

**Flip pattern** (applied in both directions):
```python
# BV internal → Tal/RAS (read)
data = np.transpose(data, (0, 2, 1))  # swap Y and X
data = data[::-1, ::-1, ::-1]         # flip all axes

# Tal/RAS → BV internal (write)
data = data[::-1, ::-1, ::-1]         # flip all axes
data = np.transpose(data, (0, 2, 1))  # swap Y and X
```

---

## VMR — 3D Anatomical (uint8, binary)

**File**: `.vmr` | **Version**: 4 | **bvbabel**: `bvbabel.vmr`

### Pre-data header (8 bytes)

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 2 | `<H` | File version (4) |
| 2 | 2 | `<H` | DimX |
| 4 | 2 | `<H` | DimY |
| 6 | 2 | `<H` | DimZ |

### Data (DimZ × DimY × DimX bytes)

Each voxel is 1 byte (`<B`, 0–225). Loop order: DimZ → DimY → DimX.

### Post-data header

| Field | Type | Description |
|-------|------|-------------|
| OffsetX/OffsetY/OffsetZ | `<h` | Offset values (v3+) |
| FramingCubeDim | `<h` | Iso-cube size (v3+) |
| PosInfosVerified | `<i` | Position info verified flag |
| CoordinateSystem | `<i` | Scanner coordinate system |
| Slice1CenterX/Y/Z | `<f` | First slice center (mm) |
| SliceNCenterX/Y/Z | `<f` | Last slice center (mm) |
| RowDirX/Y/Z | `<f` | Row direction vector |
| ColDirX/Y/Z | `<f` | Column direction vector |
| NRows, NCols | `<i` | Slice matrix dimensions |
| FoVRows, FoVCols | `<f` | Field of view (mm) |
| SliceThickness, GapThickness | `<f` | Slice/gap (mm) |
| NrOfPastSpatialTransformations | `<i` | Number of transforms |
| PastTransformation[] | varies | Name, Type, SourceFileName, NrOfValues, Values[] |
| LeftRightConvention | `<B` | 0=unknown, 1=radiological, 2=neurological |
| ReferenceSpaceVMR | `<B` | 0=unknown, 1=native, 2=ACPC, 3=Tal, 4=MNI (v4+) |
| VoxelSizeX/Y/Z | `<f` | Voxel resolution (mm) |
| VoxelResolutionVerified | `<B` | Verified flag |
| VoxelResolutionInTALmm | `<B` | In TAL mm flag |
| VMROrigV16MinValue | `<i` | Orig V16 min intensity |
| VMROrigV16MeanValue | `<i` | Orig V16 mean intensity |
| VMROrigV16MaxValue | `<i` | Orig V16 max intensity |

### bvbabel usage
```python
import bvbabel
header, data = bvbabel.vmr.read_vmr("anatomy.vmr")      # data: (Z, X, Y) uint8
bvbabel.vmr.write_vmr("output.vmr", header, data)
header, data = bvbabel.vmr.create_vmr()                   # default 256³
```

### Key notes
- Intensity range: 0–225 (uint8). Higher values → brighter in BV.
- The V16 file (same basename, `.v16` extension) stores the same data as uint16 for high-precision operations like IIHC.
- Transformation type codes: 1=rigid+scale (9 vals), 2=affine (16 vals, 4×4), 4=Talairach, 5=Un-Talairach.

---

## V16 — 3D Anatomical (uint16, binary)

**File**: `.v16` | **No version field** | **bvbabel**: `bvbabel.v16`

### Header (6 bytes)

| Offset | Bytes | Type | Field |
|--------|-------|------|-------|
| 0 | 2 | `<H` | DimX |
| 2 | 2 | `<H` | DimY |
| 4 | 2 | `<H` | DimZ |

### Data

Each voxel: `<H` (uint16, 0–65535). Same loop order as VMR (DimZ→DimY→DimX). **No post-data header**.

### bvbabel usage
```python
header, data = bvbabel.v16.read_v16("anatomy.v16")
bvbabel.v16.write_v16("output.v16", header, data)  # also accepts VMR headers
```

### Key notes
- V16 has **no post-data header** — only dimensions + raw data.
- Used by MP2RAGE denoising (stores INV1, INV2, UNI as uint16).
- BV auto-creates `.v16` from `.vmr` on first load when needed for IIHC.

---

## FMR — Functional Project (text header + STC binary data)

**File**: `.fmr` (text) | **Version**: 5–6 | **bvbabel**: `bvbabel.fmr`

The FMR is a **text file** containing key:value pairs. The actual voxel data is in a paired `.stc` file (same `Prefix`, same directory).

### Header fields

| Field | Type | Description |
|-------|------|-------------|
| FileVersion | int | File version (5 or 6) |
| NrOfVolumes | int | Number of time points |
| NrOfSlices | int | Number of slices |
| NrOfSkippedVolumes | int | Skipped initial volumes |
| Prefix | str | Basename for STC file |
| DataStorageFormat | int | 1=per-slice files, 2=single STC, 3=volume series, 4=VTC-like |
| DataType | int | 1=2-byte int, 2=4-byte float |
| TR | int | Repetition time (ms) |
| InterSliceTime | int | Time between slices (ms) |
| TE | int | Echo time (ms) |
| SliceAcquisitionOrder | str | e.g. "ascending", "descending", "interleaved" |
| ResolutionX (NrOfColumns) | int | Voxels per row |
| ResolutionY (NrOfRows) | int | Voxels per column |
| LoadAMRFile | str | Path to AMR if attached |
| InplaneResolutionX | str | In-plane resolution (mm) |
| InplaneResolutionY | str | In-plane resolution (mm) |
| SliceThickness | str | Slice thickness (mm) |
| SliceGap | str | Gap between slices (mm) |
| LeftRightConvention | str | L/R convention |

### Position information sub-section

| Field | Description |
|-------|-------------|
| PosInfosVerified | Verification flag |
| CoordinateSystem | Scanner coordinate system |
| Slice1CenterX/Y/Z | First slice center |
| SliceNCenterX/Y/Z | Last slice center |
| RowDirX/Y/Z | Row direction vector |
| ColDirX/Y/Z | Column direction vector |
| NRows, NCols | Slice matrix dims |
| FoVRows, FoVCols | Field of view |
| SliceThickness, GapThickness | Geometry |

### Transformation information sub-section

| Field | Description |
|-------|-------------|
| NrOfPastSpatialTransformations | Count |
| NameOfSpatialTransformation | Name |
| TypeOfSpatialTransformation | Type code |
| AppliedToFileName | Target file |
| NrOfTransformationValues | Count |
| Transformation matrix | 4×4 affine (16 floats) |

### Multiband information sub-section

| Field | Description |
|-------|-------------|
| FirstDataSourceFile | Source file |
| MultibandSequence | Sequence type |
| MultibandFactor | MB factor |
| SliceTimingTableSize | Number of timing entries |
| Slice timings | List of timing values (ms) |
| AcqusitionTime | Total acquisition time |

### bvbabel usage
```python
header, data = bvbabel.fmr.read_fmr("task_run.fmr")
# data shape: (X, Y, slices, volumes) with rearrange_data_axes=True
bvbabel.fmr.write_fmr("output.fmr", header, data)
header, data = bvbabel.fmr.create_fmr()
```

---

## STC — Slice Time Course (binary, no header)

**File**: `.stc` | **bvbabel**: `bvbabel.stc`

Raw binary data — **no header at all**. All metadata comes from the paired `.fmr` file.

Data layout (on disk): `(nr_slices, nr_volumes, res_x, res_y)`. With `rearrange_data_axes=True`, returned as `(res_x, res_y, nr_slices, nr_volumes)`.

| Parameter | Source | Description |
|-----------|--------|-------------|
| nr_slices | FMR header | NrOfSlices |
| nr_volumes | FMR header | NrOfVolumes |
| res_x | FMR header | ResolutionX |
| res_y | FMR header | ResolutionY |
| data_type | FMR header | 1=int16, 2=float32 |

### bvbabel usage
```python
data = bvbabel.stc.read_stc("task_run.stc",
    nr_slices=72, nr_volumes=240, res_x=104, res_y=104, data_type=2)
bvbabel.stc.write_stc("output.stc", data, data_type=2)
```

---

## VTC — Volume Time Course (binary)

**File**: `.vtc` | **Version**: 3 | **bvbabel**: `bvbabel.vtc`

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<h` | 3 |
| Source FMR name | var-str | Source FMR path |
| Protocol attached | `<h` | 1 if PRT attached |
| Protocol name | var-str | PRT file path |
| Current protocol index | `<h` | Protocol index |
| Data type | `<h` | 1=int16, 2=float32 |
| Nr time points | `<h` | Number of volumes |
| VTC resolution relative to VMR | `<h` | 1, 2, or 3 |
| XStart | `<h` | Bounding box start X |
| XEnd | `<h` | Bounding box end X |
| YStart | `<h` | Bounding box start Y |
| YEnd | `<h` | Bounding box end Y |
| ZStart | `<h` | Bounding box start Z |
| ZEnd | `<h` | Bounding box end Z |
| L-R convention | `<B` | 0=unknown, 1=radiological, 2=neurological |
| Reference space | `<B` | 0=unknown, 1=native, 2=ACPC, 3=Tal, 4=MNI |
| TR (ms) | `<f` | Repetition time |

### Data layout (on disk)
Loop order: DimZ → DimY → DimX → DimT. With `rearrange_data_axes=True`: flipped + transposed (0, 2, 1, 3).

```python
DimX = (XEnd - XStart) // VTC_res
DimY = (YEnd - YStart) // VTC_res
DimZ = (ZEnd - ZStart) // VTC_res
```

### bvbabel usage
```python
header, data = bvbabel.vtc.read_vtc("task_MNI.vtc")
bvbabel.vtc.write_vtc("output.vtc", header, data)
header, data = bvbabel.vtc.create_vtc()
```

---

## TRF — Transformation (text)

**File**: `.trf` | **Version**: 8 | **bvbabel**: `bvbabel.trf`

### Header fields

| Field | Type | Description |
|-------|------|-------------|
| FileVersion | int | 8 |
| DataFormat | str | "Matrix" |
| TransformationType | int | 1=rigid+scale, 2=affine, 3=MNI, 4=Talairach, 5=Untal |
| CoordinateSystem | int | 0-1 |
| NSlicesFMRVMR | int | (type 1 only) |
| SlThickFMRVMR | float | (type 1 only) |
| SlGapFMRVMR | float | (type 1 only) |
| CreateFMR3DMethod | int | (type 1 only) |
| AlignmentStep | int | 1=initial, 2=fine (type 1 only) |
| ExtraVMRTransf | int | Extra transform flag (v5+) |
| SourceFile | str | Source FMR/VMR path |
| TargetFile | str | Target VMR path |

### Data
4×4 affine matrix stored as 16 decimal values (4 rows × 4 columns), plus optional ExtraVMRTransf matrix.

### bvbabel usage
```python
header, data = bvbabel.trf.read_trf("coreg_IA.trf")
# data["Matrix"] = 4×4 numpy array
# data may also have "ExtraVMRTransf" key
bvbabel.trf.write_trf("output.trf", header, data)
```

### Coregistration TRF chain
- `*_IA.trf` — initial alignment (DICOM geometry-based)
- `*_FA.trf` — fine alignment (iterative intensity/BBR)
- `*_IA-TO-FA.trf` — combined IA + FA
- `*_MNI.trf` — MNI normalization transform
- `*_ACPC.trf` — AC-PC transform

---

## PRT — Protocol (text)

**File**: `.prt` | **Version**: 2–3 | **bvbabel**: `bvbabel.prt`

### Header fields

| Field | Description |
|-------|-------------|
| FileVersion | 2 or 3 |
| ResolutionOfTime | "msec" or "Volumes" |
| Experiment | Experiment name |
| BackgroundColor | RGB triplet |
| TextColor | RGB triplet |
| TimeCourseColor | RGB triplet |
| TimeCourseThick | Line thickness |
| ReferenceFuncColor | RGB triplet |
| ReferenceFuncThick | Line thickness |
| ParametricWeights | 1 if parametric (v3+) |
| NrOfConditions | Number of conditions |

### Data (per condition)
```
ConditionName
NrOfOccurrences
time_start  time_stop  [parametric_weight]
Color: R G B
```

Time units: if `ResolutionOfTime == "Seconds"`, stored values are multiplied by 1000 (converted to ms).

### bvbabel usage
```python
header, data_prt = bvbabel.prt.read_prt("protocol.prt")
# data_prt[i]["NameOfCondition"], ["Time start"], ["Time stop"], ["Color"]
bvbabel.prt.write_prt("output.prt", header, data_prt)
```

---

## SDM — Design Matrix (text)

**File**: `.sdm` | **Version**: 1 | **bvbabel**: `bvbabel.sdm`

### Header fields

| Field | Description |
|-------|-------------|
| FileVersion | 1 |
| NrOfPredictors | Number of predictors (columns) |
| NrOfDataPoints | Number of time points (rows) |
| IncludesConstant | 1 if constant included |
| FirstConfoundPredictor | Index of first confound |

### Data layout
```
Color: R1 G1 B1   R2 G2 B2   ...   Rn Gn Bn
"Predictor1" "Predictor2" ... "PredictorN"
val1_1  val1_2  ...  val1_n
...
valM_1  valM_2  ...  valM_n
```

Used for both design matrices AND motion parameter files (`*_3DMC.sdm`).

### bvbabel usage
```python
header, data_sdm = bvbabel.sdm.read_sdm("design.sdm")
# data_sdm[i]["NameOfPredictor"], ["ColorOfPredictor"], ["ValuesOfPredictor"]
bvbabel.sdm.write_sdm("output.sdm", header, data_sdm)
```

---

## MDM — Multi-Design Matrix (text)

**File**: `.mdm` | **Version**: 3 | **bvbabel**: `bvbabel.mdm` (at bvbabel root)

### Header fields

| Field | Description |
|-------|-------------|
| FileVersion | 3 |
| TypeOfFunctionalData | "VTC" or "MTC" |
| RFX-GLM | 0=FFX, 1=RFX |
| PSCTransformation | 1=percent signal change |
| zTransformation | 1=z-transform |
| SeparatePredictors | 0=same, 1=separate studies, 2=separate subjects |
| NrOfStudies | Number of studies |

### Data (per study)
```
"PathNameSSM" "PathNameData" "PathNameSDM"    (MTC)
"PathNameData" "PathNameSDM"                   (VTC)
```

### Analysis types
| Type | RFX-GLM | SeparatePredictors |
|------|---------|-------------------|
| FFX | 0 | 0 |
| SPST (separate studies) | 0 | 1 |
| SPSB (separate subjects) | 0 | 2 |
| RFX (random effects) | 1 | 2 |

### bvbabel usage
```python
import bvbabel.mdm as mdm_lib  # note: at bvbabel root, not bvbabel.bvbabel
header, data = mdm_lib.read_mdm("group.mdm")
mdm_lib.write_mdm("output.mdm", header, data)
```

---

## VMP — Volumetric Map (binary)

**File**: `.vmp` | **Version**: 2–4 | **bvbabel**: `bvbabel.vmp`

Statistical or parameter maps in VMR/VTC space (3D volumes). Each "map" is a separate 3D sub-volume.

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<h` | 2–4 |
| Nr maps | `<h` | Number of sub-maps |
| Map type | `<i` | 1=t, 2=corr, 3=cross-corr, 4=F, 5=z, 11=PSC, 12=ICA, 14=Chi², 15=beta, 16=p, 21=MD, 22=FA, 25=polar angle |
| XStart, XEnd | `<h` | Bounding box X |
| YStart, YEnd | `<h` | Bounding box Y |
| ZStart, ZEnd | `<h` | Bounding box Z |
| VTC res relative to VMR | `<h` | Resolution |
| Nr valid voxels | `<i` | Count of in-bounds voxels |

### Per-map fields
| Field | Description |
|-------|-------------|
| Map type | Statistical type code |
| Cluster size | Minimum cluster size |
| Threshold min/max | Display thresholds |
| Degrees of freedom 1/2 | DF for statistics |
| Show positive negative | Display flag (v5+) |
| Bonferroni correction value | Correction value |
| RGB positive min/max | Color for positive values |
| RGB negative min/max | Color for negative values (v4+) |
| RGB or LUT | 0=RGB, 1=LUT |
| LUT file | Lookup table path |
| Color transparency | Alpha (0–1) |
| Name | Map name |

### bvbabel usage
```python
header, data = bvbabel.vmp.read_vmp("stats.vmp")
bvbabel.vmp.write_vmp("output.vmp", header, data)
```

---

## SMP — Surface Map (binary)

**File**: `.smp` | **Version**: 5 | **bvbabel**: `bvbabel.smp`

Statistical maps on mesh vertices (1D per map).

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<h` | 5 |
| Nr vertices | `<i` | Number of mesh vertices |
| Nr maps | `<h` | Number of sub-maps |
| SRF file | var-str | Path to associated SRF mesh |

### Per-map fields
Same statistical codes and threshold/color fields as VMP maps, plus:
- `CC nr lags`, `CC min lag`, `CC max lag`, `CC overlay` (for map type 3, cross-correlation)
- `Threshold include greater than max` (v4+)

### bvbabel usage
```python
header, data = bvbabel.smp.read_smp("stats.smp")
# data shape: (Nr vertices, Nr maps), float32
bvbabel.smp.write_smp("output.smp", header, data)
```

---

## SRF — Surface Mesh (binary)

**File**: `.srf` | **Version**: 1.0+ (float) | **bvbabel**: `bvbabel.srf`

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<f` | 1.0+ |
| Surface type | `<i` | Mesh type code |
| Nr vertices | `<i` | Vertex count |
| Nr triangles | `<i` | Face (triangle) count |
| Mesh center X/Y/Z | `<f` | Mesh centroid |

### Data
| Component | Type | Shape | Description |
|-----------|------|-------|-------------|
| vertices | `<f` | (Nr vertices, 3) | XYZ coordinates |
| vertex normals | `<f` | (Nr vertices, 3) | Normal vectors |
| Vertex convex curvature R/G/B | `<f` | scalar (v1.0+) | Curvature color |
| faces | `<i` | (Nr triangles, 3) | Triangle vertex indices |
| vertex colors | `<B` | (Nr vertices, 4) | BGRA colors |
| vertex neighbors | list | (Nr vertices, var) | Neighbor vertex indices |
| strip sequence | — | — | Strip sequence |

### bvbabel usage
```python
header, mesh_data = bvbabel.srf.read_srf("cortex.srf")
# mesh_data["vertices"], ["vertex normals"], ["faces"], ["vertex colors"]
bvbabel.srf.write_srf("output.srf", header, mesh_data)
```

---

## MSK — Mask (binary)

**File**: `.msk` | **bvbabel**: `bvbabel.msk`

Voxel mask — simple binary format. Each voxel is 1 byte (`<B`, 0 or 1).

### Header

| Field | Type | Description |
|-------|------|-------------|
| VTC resolution | `<h` | Resolution relative to VMR |
| XStart | `<h` | Bounding box |
| XEnd | `<h` | |
| YStart | `<h` | |
| YEnd | `<h` | |
| ZStart | `<h` | |
| ZEnd | `<h` | |

### Data
DimZ × DimY × DimX bytes (uint8, 0 or 1). Same loop order as VMR/VTC.

---

## GLM — General Linear Model Results (binary)

**File**: `.glm` | **bvbabel**: `bvbabel.glm`

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<h` | 4 |
| Type | `<B` | 0=FMR-STC, 1=VMR-VTC, 2=SRF-MTC |
| RFX-GLM | `<B` | 0=standard, 1=random effects |
| Nr subjects | `<i` | (RFX only) |
| Nr predictors per subject | `<i` | (RFX only) |
| Nr time points | `<i` | |
| Nr all predictors | `<i` | |
| Nr studies | `<i` | |
| Serial correlation | `<B` | 0=none, 1=AR(1), 2=AR(2) |
| ... | | (additional fields for design matrix, contrasts, etc.) |

### Data arrays
| Array | Description |
|-------|-------------|
| R² (multiple correlation) | Goodness-of-fit per voxel |
| SS (sum-of-squares) | Total SS per voxel |
| Beta | Beta weights (per predictor, per voxel) |
| SS_XiY | Covariation per predictor |
| Mean TC | Mean time course value |
| AR lag | Autoregression lag values |

### Key formulas
```python
VAR_residuals = SS * (1 - R2) / (Nr_time_points - Nr_all_predictors)
t = c'b / sqrt(VAR_residuals * c' * inv_X'X * c)
```

---

## MTC — Mesh Time Course (binary)

**File**: `.mtc` | **Version**: 1 | **bvbabel**: `bvbabel.mtc`

Vertex-wise time courses extracted from VTC onto a surface mesh.

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<i` | 1 |
| Nr vertices | `<i` | Number of mesh vertices |
| Nr time points | `<i` | Number of volumes |
| VTC name | var-str | Source VTC |
| PRT name | var-str | Protocol file |
| Hemodynamic delay | `<i` | Delay parameter |
| TR | `<f` | Repetition time (ms) |
| delta | `<f` | HRF delta |
| tau | `<f` | HRF tau |
| segment size | `<i` | Segment size |
| segment offset | `<i` | Segment offset |
| Datatype | `<B` | 1=float32 |

### Data
(Nr vertices, Nr time points) float32 array.

---

## GTC — Grid Time Course (binary)

**File**: `.gtc` | **Version**: 1 | **bvbabel**: `bvbabel.gtc`

Depth-grid sampled time courses (for laminar/cortical depth analysis).

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<i` | 1 |
| DimD | `<i` | Depth dimension |
| DimX | `<i` | X dimension |
| DimY | `<i` | Y dimension |
| DimT | `<i` | Time dimension |

### Data
Loop order: DimD → DimY → DimX → DimT. 4D int32 array.

---

## SSM — Sphere-to-Sphere Mapping (binary)

**File**: `.ssm` | **Version**: 2 | **bvbabel**: `bvbabel.ssm`

Maps vertices from one sphere mesh to another.

### Header

| Field | Type | Description |
|-------|------|-------------|
| File version | `<h` | 2 |
| Nr vertices 1 | `<i` | Source mesh vertex count |
| Nr vertices 2 | `<i` | Target mesh vertex count |

### Data
1D int32 array mapping each source vertex to a target vertex index.

---

## POI — Patches of Interest (text)

**File**: `.poi` | **Version**: 2 | **bvbabel**: `bvbabel.poi`

Surface-based patches (sets of mesh vertices).

### Header

| Field | Description |
|-------|-------------|
| FileVersion | 2 |
| FromMeshFile | Source SRF path |
| NrOfMeshVertices | Total vertices in mesh |
| NrOfPOIs | Number of patches |

### Per-POI fields
```
NameOfPOI: "name"
InfoTextFile: "path"
ColorOfPOI: R G B
LabelVertex: vertex_index
NrOfVertices: count
vertex_index_1
vertex_index_2
...
```

---

## VOI — Volumes of Interest (binary, wip)

**File**: `.voi` | **bvbabel**: `bvbabel.voi`

3D volume-based ROIs. **Work in progress** in bvbabel — read support exists.

---

## Cross-reference: which formats each pipeline skill produces

| Pipeline Skill | Input Formats | Output Formats |
|---------------|---------------|----------------|
| `bv-dicom-setup` | DICOM | DICOM (renamed) |
| `bv-fmr-creation` | DICOM | FMR, STC, NIfTI |
| `bv-fmri-preprocessing` | FMR, STC | FMR, STC, SDM (motion params) |
| `bv-distortion-correction` | FMR, STC | FMR, STC, NIfTI |
| `bv-anatomical-pipeline` | DICOM, VMR, V16 | VMR, V16, TRF, TAL |
| `bv-coregistration-vtc` | FMR, STC, VMR | TRF, VTC, MDM |

## Common bvbabel patterns

### Reading any BV file
```python
import bvbabel

# Binary formats: header is dict, data is numpy array(s)
header, data = bvbabel.vmr.read_vmr("file.vmr")
header, data = bvbabel.v16.read_v16("file.v16")
header, data = bvbabel.vtc.read_vtc("file.vtc")
header, data = bvbabel.vmp.read_vmp("file.vmp")
header, data = bvbabel.smp.read_smp("file.smp")
header, mesh = bvbabel.srf.read_srf("file.srf")
header, data = bvbabel.msk.read_msk("file.msk")
header, data = bvbabel.mtc.read_mtc("file.mtc")
header, data = bvbabel.glm.read_glm("file.glm")
header, data = bvbabel.ssm.read_ssm("file.ssm")

# Text formats: header is dict, data is list of dicts or numpy
header, data = bvbabel.fmr.read_fmr("file.fmr")
header, data = bvbabel.trf.read_trf("file.trf")
header, data = bvbabel.prt.read_prt("file.prt")
header, data = bvbabel.sdm.read_sdm("file.sdm")
header, data = bvbabel.poi.read_poi("file.poi")

# STC needs parameters from FMR header
fmr_header, _ = bvbabel.fmr.read_fmr("file.fmr")
data = bvbabel.stc.read_stc("file.stc",
    nr_slices=fmr_header["NrOfSlices"],
    nr_volumes=fmr_header["NrOfVolumes"],
    res_x=fmr_header["ResolutionX"],
    res_y=fmr_header["ResolutionY"],
    data_type=fmr_header["DataType"])
```

### Creating default files
```python
# Most formats have create_*() returning (header, data) with defaults
header, data = bvbabel.vmr.create_vmr()
header, data = bvbabel.vmp.create_vmp()
header, data = bvbabel.smp.create_smp(nr_maps=2, nr_vertices=81924)
header, data = bvbabel.sdm.create_sdm()
header, data = bvbabel.fmr.create_fmr()
header, data = bvbabel.vtc.create_vtc()
```

### FMR ↔ NIfTI conversion (for FSL topup)
```python
import nibabel as nb
import numpy as np

# FMR → NIfTI
fmr_header, data = bvbabel.fmr.read_fmr("task.fmr")
img = nb.Nifti1Image(data, affine=np.eye(4))
nb.save(img, "task.nii.gz")

# NIfTI → FMR (using reference FMR for header)
ref_header, _ = bvbabel.fmr.read_fmr("reference.fmr")
nii_data = nb.load("corrected.nii.gz").get_fdata()
ref_header["Prefix"] = "new_prefix"
bvbabel.fmr.write_fmr("new.fmr", ref_header, nii_data)
```

### VMR ↔ V16 conversion
```python
# VMR → V16
vmr_header, vmr_data = bvbabel.vmr.read_vmr("anatomy.vmr")
bvbabel.v16.write_v16("anatomy.v16", vmr_header, vmr_data)

# V16 → VMR
v16_header, v16_data = bvbabel.v16.read_v16("anatomy.v16")
vmr_header["DimX"] = v16_header["DimX"]  # VMR header needs these fields
vmr_header["DimY"] = v16_header["DimY"]
vmr_header["DimZ"] = v16_header["DimZ"]
bvbabel.vmr.write_vmr("anatomy.vmr", vmr_header, v16_data)
```

## Gotchas

- **Axis order**: BV internal is LIP+, bvbabel defaults to RAS+ on read. Always check `rearrange_data_axes` parameter — set `False` for raw BV axes.
- **STC has no header**: Must always read the paired FMR first to get dimensions.
- **V16 has no post-data header**: Unlike VMR, V16 only stores DimX/Y/Z + raw data. Don't expect position info or transformation history.
- **FMR text file path**: The FMR references STC by `Prefix`. Both must be in the same directory.
- **TRF TransformationType matters**: IA (type 1), FA (type 1), MNI (type 3), Tal (type 4). Don't mix them.
- **VMP/SMP map type codes**: These determine how BV visualizes the map. Wrong type = wrong coloring/thresholding.
- **MDM module location**: `bvbabel.mdm` is at the bvbabel package root (not in `bvbabel.bvbabel`). Import with `import bvbabel.mdm` or use `mdm.py` directly from `/tmp/bvbabel/mdm.py`.
- **Data type enums**: int16 (1) vs float32 (2) matters for VTC/STC. float VTC may not render in older BV versions.
- **File version evolution**: Newer versions add fields at the END of headers. Backward-compatible reads should check the version before expecting version-specific fields.
