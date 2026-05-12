"""Listener handler dispatch — merged hash table.

Every handler module exports a ``HANDLERS`` dict mapping action-string →
callable.  This init merges them into ``ALL_HANDLERS`` so the listener can
do a single O(1) lookup with zero branching.
"""

from .core_handlers import HANDLERS as CORE
from .anatomy_handlers import HANDLERS as ANATOMY
from .fmri_handlers import HANDLERS as FMRI

ALL_HANDLERS: dict[str, callable] = {}
ALL_HANDLERS.update(CORE)
ALL_HANDLERS.update(ANATOMY)
ALL_HANDLERS.update(FMRI)
