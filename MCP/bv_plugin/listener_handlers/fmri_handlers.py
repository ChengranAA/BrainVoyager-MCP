"""fMRI action handlers — MDM / VTC / FMR / DMR / project (will grow).

Currently the smallest module.  Populate as FMR creation, VTC coregistration,
temporal filtering, DMR, and project/workflow tools are added.
"""

import json


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"


def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


# ── MDM / VTC ──────────────────────────────────────────────────────────────


def _get_vtcs_of_mdm(data: dict) -> str:
    mdm = data.get("mdm_file", "")
    if not mdm:
        return _bad("Missing mdm_file.")
    vtcs = bv.get_vtcs_of_mdm(mdm)
    return _ok(json.dumps({"result": list(vtcs)}))


# ── dispatch table ─────────────────────────────────────────────────────────

HANDLERS: dict[str, callable] = {
    "get_vtcs_of_mdm": _get_vtcs_of_mdm,
}
