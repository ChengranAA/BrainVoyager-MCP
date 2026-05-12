"""BV Core MCP Server — document management, DICOM ops, UI & shell."""
import os
from mcp.server.fastmcp import FastMCP
from MCP._shared.bv_client import call_bv, call_bv_with_path

mcp = FastMCP(
    "BrainVoyager Core",
    instructions=(
        "Most operations are fast. DICOM defacing and large renames may take "
        "longer. Long-running tools accept a timeout_seconds parameter."
    ),
)


@mcp.tool()
def open_bv_document(file_path: str) -> str:
    """Open a document in BrainVoyager. Supports .vmr, .fmr, .dmr, and NIfTI."""
    return call_bv_with_path("open_document", file_path, timeout=5)


@mcp.tool()
def open_bv_document_advanced(
    file_path: str, close_current_doc: bool = False,
    remove_current_doc: bool = False,
) -> str:
    """Open a document with options to close/remove the currently active one."""
    return call_bv_with_path(
        "open", file_path, timeout=5,
        close_current_doc=close_current_doc,
        remove_current_doc=remove_current_doc)


@mcp.tool()
def close_all_bv_documents() -> str:
    """Close every open document in BrainVoyager's workspace."""
    return call_bv("close_all", timeout=5)


@mcp.tool()
def get_bv_document_attributes() -> str:
    """Return all attributes of the currently active document."""
    return call_bv("get_doc_attributes", timeout=15)


@mcp.tool()
def get_bv_methods() -> str:
    """Return a list of every method supported by the BrainVoyager API."""
    return call_bv("methods", timeout=5)


@mcp.tool()
def describe_bv_method(method_name: str) -> str:
    """Return documentation for a specific BrainVoyager API method."""
    return call_bv("describe_method", timeout=5, method_name=method_name)


# ── DICOM Operations ──────────────────────────────────────────────────────


@mcp.tool()
def rename_bv_dicoms(directory: str, timeout_seconds: int = 30) -> str:
    """Rename DICOM files to standard BrainVoyager format.

    PatientsName-SeriesNumber-VolumeNumber-ImageNumber.dcm"""
    return call_bv_with_path("rename_dicoms", directory,
                             timeout=timeout_seconds)


@mcp.tool()
def anonymize_bv_dicoms(
    directory: str, anonymized_patient_name: str, timeout_seconds: int = 60,
) -> str:
    """Rename DICOMs to standard format AND replace the patient name."""
    return call_bv_with_path(
        "anonymize_dicoms", directory, timeout=timeout_seconds,
        patient_name=anonymized_patient_name)


@mcp.tool()
def deface_bv_anatomical_dicoms(
    input_directory: str, output_directory: str, timeout_seconds: int = 120,
) -> str:
    """Deface anatomical DICOM images (requires 1mm iso-voxel data).

    Temporarily normalizes to MNI, applies defacing mask in native space."""
    return call_bv_with_path(
        "deface_anat_dicoms", input_directory, timeout=timeout_seconds,
        output_directory=os.path.expanduser(output_directory))


# ── Log Pane ──────────────────────────────────────────────────────────────


@mcp.tool()
def show_bv_log_pane() -> str:
    """Show the BrainVoyager Log pane."""
    return call_bv("show_log_pane", timeout=5)


@mcp.tool()
def hide_bv_log_pane() -> str:
    """Hide the BrainVoyager Log pane."""
    return call_bv("hide_log_pane", timeout=5)


@mcp.tool()
def print_to_bv_log(text: str) -> str:
    """Print a message to the BrainVoyager Log pane."""
    return call_bv("print_to_log", timeout=5, text=text)


# ── Shell ─────────────────────────────────────────────────────────────────


@mcp.tool()
def run_bv_shell_command(shell_command: str, timeout_seconds: int = 120) -> str:
    """Run a shell command and return its stdout.

    BV blocks until the command completes. Set timeout_seconds carefully —
    there is no way to kill a runaway command from outside."""
    return call_bv("run_cmd", timeout=timeout_seconds,
                   shell_command=shell_command)


# ── Application Control ───────────────────────────────────────────────────


@mcp.tool()
def exit_bv() -> str:
    """Shut down BrainVoyager. Use with caution."""
    return call_bv("exit", timeout=5)


# ── Dialogs ───────────────────────────────────────────────────────────────


@mcp.tool()
def show_bv_message_box(message: str) -> str:
    """Show a modal message box in BrainVoyager."""
    return call_bv("show_message_box", timeout=5, message=message)


@mcp.tool()
def show_bv_timeout_message_box(message: str, duration: int = 3000) -> str:
    """Show a message box that auto-closes after *duration* ms."""
    return call_bv("show_timeout_message_box", timeout=5,
                   message=message, duration=duration)


# ── Window Control ────────────────────────────────────────────────────────


@mcp.tool()
def move_bv_window(new_x: int, new_y: int) -> str:
    """Move the BrainVoyager main window on screen."""
    return call_bv("move_window", timeout=5, new_x=new_x, new_y=new_y)


@mcp.tool()
def resize_bv_window(new_width: int, new_height: int) -> str:
    """Resize the BrainVoyager main window."""
    return call_bv("resize_window", timeout=5,
                   new_width=new_width, new_height=new_height)


# ── File / Directory Choosers ─────────────────────────────────────────────


@mcp.tool()
def choose_bv_directory(instruction: str = "Select a directory") -> str:
    """Open a directory-chooser dialog in BrainVoyager."""
    return call_bv("choose_directory", timeout=60,
                   instruction=instruction)


@mcp.tool()
def choose_bv_file(instruction: str = "Select a file",
                   filter: str = "*") -> str:
    """Open a file-chooser dialog in BrainVoyager."""
    return call_bv("choose_file", timeout=60,
                   instruction=instruction, filter=filter)


if __name__ == "__main__":
    mcp.run()
