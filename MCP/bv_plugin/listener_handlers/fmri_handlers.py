"""fMRI action handlers — MDM / VTC / FMR / DMR / project.

``_bv`` is injected by ``listener_handlers.set_bv()`` at listener startup.
"""

import json

# Injected by set_bv() — do NOT use bare `bv` as an implicit global.
_bv = None


def _ok(body: str = "") -> str:
    return f"HTTP/1.1 200 OK\n\n{body}"

def _bad(body: str) -> str:
    return f"HTTP/1.1 400 Bad Request\n\n{body}"


def _get_vtcs_of_mdm(data: dict) -> str:
    mdm = data.get("mdm_file", "")
    if not mdm:
        return _bad("Missing mdm_file.")
    vtcs = _bv.get_vtcs_of_mdm(mdm)
    return _ok(json.dumps({"result": list(vtcs)}))


HANDLERS: dict[str, callable] = {
    "get_vtcs_of_mdm": _get_vtcs_of_mdm,
}
