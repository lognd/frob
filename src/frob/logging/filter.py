import logging


# frob:doc docs/modules/logging.md#public-api
# frob:waive COV007 reason="docs/modules/logging.md's Public API section individually \
# frob:describes this private filter and its .filter method by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:invariant INV-016
# invariant spec: [INV-016](invariants/INV-016.md)
# frob:tests tests/unit/test_logging_module.py::test_below_level_filter
# frob:ticket T-1038
# frob:waive AFFECT001 reason="T-1038: OPAQUE001 fix-or-waive hardening -- added a \
# reasoned frob:waive comment above the existing getattr(logging, below.upper()) call \
# in __init__; the documented level-below-filter contract and behavior are unchanged, \
# nothing for docs/modules/logging.md#public-api to update"
class _BelowLevelFilter(logging.Filter):
    """Pass records strictly below `below` level (used to keep stdout clean)."""

    # frob:ticket T-1038
    # frob:ticket T-1659
    # frob:waive OPAQUE001 reason="T-1038: below is a log-level name from this \
    # process's own dictConfig-declared logging setup, not attacker/external input -- \
    # the standard getattr(logging, LEVEL_NAME) idiom stdlib's own \
    # logging.getLevelName docs recommend for resolving a level by name. T-1659: moved \
    # up from directly above the getattr() call inside __init__'s own body -- \
    # frob.graph.dsl's _enclosing_src mis-binds a waive comment sitting as the LAST \
    # line of a method body to the class's NEXT sibling method instead of the method \
    # it is textually inside of (confirmed via build_graph: the old placement resolved \
    # to _BelowLevelFilter.filter, not .__init__ -- see the dsl.py bug filed \
    # separately). Placed here, directly above the def, it binds to __init__ via the \
    # ordinary following-symbol rule, which does not depend on the buggy path."
    def __init__(self, below: str) -> None:
        super().__init__()
        self._below = getattr(logging, below.upper())

    def filter(self, record: logging.LogRecord) -> bool:
        # frob:doc docs/modules/logging.md#public-api
        return record.levelno < self._below
