"""BV fMRI MCP Server — VTC, MDM, FMR, DMR & project/workflow tools.

Today this is the smallest server (one tool).  It will grow as FMR creation,
VTC coregistration, temporal filtering, DMR preprocessing, and project-level
workflow tools are populated from the BrainVoyager API.
"""

import os
from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_client import call_bv, call_bv_with_path

mcp = FastMCP(
    "BrainVoyager fMRI",
    instructions=(
        "Future tools (FMR creation, VTC coregistration, DMR preprocessing, "
        "project workflows) may run long computations. Your MCP client may "
        "timeout before BV finishes — check the Log pane. "
        "Long-running tools accept a timeout_seconds parameter."
    ),
)

# ═══════════════════════════════════════════════════════════════════════════
# MDM / VTC
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def get_vtcs_of_mdm(mdm_file: str) -> str:
    """Return every VTC file path referenced inside an MDM (multi-design-matrix)
    file.

    Args:
        mdm_file: Path to the ``.mdm`` file.
    """
    return call_bv_with_path("get_vtcs_of_mdm", mdm_file, timeout=10)


# ═══════════════════════════════════════════════════════════════════════════
# TODO — populate from the BV API as these are needed
# ═══════════════════════════════════════════════════════════════════════════
#
#   FMR creation:        create_fmr_dicom, create_fmr_dicom_nifti_bids
#   VTC coregistration:  coregister_fmr_to_vmr, create_vtc_in_native_space
#   Temporal filtering:  filter_temporal_highpass_glm_fourier / _dct
#   DMR creation:        create_dmr_dicom, create_dmr_dicom_nifti_bids
#   Project/workflow:    create_project, run_workflow, subject_data, group_data
#


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run()
