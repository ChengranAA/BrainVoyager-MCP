"""Listener handler dispatch — merged hash table with explicit bv injection.

``set_bv(bv_obj)`` must be called once before any handler fires.  It pushes
the BrainVoyager object into every handler module so they don't rely on an
implicit global.  This makes handlers testable outside BV.
"""

from . import core_handlers, anatomy_handlers, fmri_handlers


def set_bv(bv_obj):
    """Inject the BV scripting object into all handler modules."""
    core_handlers._bv = bv_obj
    anatomy_handlers._bv = bv_obj
    fmri_handlers._bv = bv_obj


ALL_HANDLERS: dict[str, callable] = {}
ALL_HANDLERS.update(core_handlers.HANDLERS)
ALL_HANDLERS.update(anatomy_handlers.HANDLERS)
ALL_HANDLERS.update(fmri_handlers.HANDLERS)
