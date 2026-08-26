"""`frob.strata._sync_may` -- shared `.strata` node/store body span scanner.

T-2920: this module used to be SYS100's core+extended auto-fix WRITER
(T-1531/T-1545) -- `sync_may_report`/`apply_sync_may`/`sync_may_extended_
report`/`apply_sync_may_extended`/`WholeNodeMayGrantDiff` silently widened
a node's declared `may "<kind>" via [...]` grant to cover whatever
capability the code was observed exercising. T-1623/T-1628 accepted that
as deliberate policy at the time ("may= capability sync is DIFFERENT,
deliberate, live work... and stays"). T-2922 (security, critical) unwired
the only caller of that writer (`frob.gates._fix_engine_sync`) on the
user's explicit instruction: a `may=` list is a CEILING a human controls,
and an auto-fix that raises the ceiling to match observed behavior is a
ratchet with no teeth. T-2935 (filed under the T-2920 epic) completes that reversal by
deleting the writer itself -- confirmed dead (zero importers anywhere in
the repo, `git grep` verified) once T-2922 landed. SYS100 the detector
(`frob.strata._selfconform`) is unaffected; only the auto-fix is gone,
and stays gone -- `frob.strata._shrink` (T-2923) is this repo's ONLY
live `.strata`-mutating auto-fix now, and it only ever narrows.

What survives this deletion: `_NODE_HEADER_RE`/`node_body_span` below,
the brace-depth `.strata` node/store body scanner T-1895 made this
module's single shared home for (originally extracted from the deleted
`_sync_interface.py`, T-1870) -- `frob.strata._shrink` (T-2923) is its
one remaining real importer, reusing the exact same text-scan approach
this module's own (now-deleted) writers used to locate a node's grant
lines without a full `.strata` re-serialize. This module's name is kept
rather than renamed, since a rename would just move the T-1895
DUP001-avoidance precedent's citation trail without changing anything
real about what lives here.
"""
# frob:ticket T-2935

from __future__ import annotations

import re

from frob.logging import get_logger

_log = get_logger(__name__)

#: One node OR store header line, e.g. `node cli : trusted {` or
#: `store tickets_ledger : trusted {` -- captures the id so a `.strata`
#: file's raw text can be searched WITHOUT re-parsing (that would lose
#: comments); the parser/elaborator is only used to compute the real/
#: declared surface, never to regenerate this file's text. `store` blocks
#: are matched identically to `node` blocks for the same reason the
#: former `_sync_interface.py` matched them identically (T-1425): SYS100
#: treats a store as a first-class subject the same as any node.
_NODE_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:node|store)\s+(?P<id>\S+)\b[^{]*\{\s*$"
)


# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/gates.md, whose own SCOPE002 closure (every OTHER symbol that \
# monolithic shared doc file describes) is out of proportion to pull into T-1895's \
# two-file extraction scope for one brace-depth scanner; docs/modules/gates.md was \
# also under a live cross-worktree lease (T-1579) at the time this ticket ran, \
# matching the same scope-closure tension SCANNED_BASES documents in _rule_id_scan.py \
# -- this function's own docstring is the authoritative description"
# frob:tests tests/unit/strata/test_sync_may.py::TestNodeBodySpan.test_flat_body_returns_closing_brace_line kind="unit"  # noqa: E501
# frob:tests tests/unit/strata/test_sync_may.py::TestNodeBodySpan.test_nested_braces_do_not_close_early kind="unit"  # noqa: E501
# frob:tests tests/unit/strata/test_sync_may.py::TestNodeBodySpan.test_malformed_input_returns_last_line_best_effort kind="unit"  # noqa: E501
def node_body_span(lines: list[str], header_idx: int) -> int:
    """The line index of the `}` that closes the node body opened at
    `lines[header_idx]` (which itself ends in `{`), brace-depth matched so a
    nested `on crash { ... }`/`on breach { ... }`/`on deploy { ... }`
    sub-block's own braces do not terminate the search early. T-1895:
    made public (was `_node_body_span`) so a second module could import
    this ONE brace-depth scanner instead of keeping its own byte-identical
    copy -- both used to independently mirror the deleted
    `_sync_interface.py`'s own copy of the same 7-line scanner. T-2920:
    the second importer used to be `frob.gates._fix_engine_sync` (T-1531's
    own SYS100 writer, deleted); `frob.strata._shrink` (T-2923) is this
    function's current real importer."""
    depth = 1
    for idx in range(header_idx + 1, len(lines)):
        # frob:waive PERF002 reason="each line is a different string every iteration \
        # -- nothing to hoist or cache; one-pass O(n) brace-depth scan, not a repeated \
        # identical query"
        depth += lines[idx].count("{") - lines[idx].count("}")
        if depth == 0:
            return idx
    return len(lines) - 1  # malformed input: no matching close, best effort


__all__ = [
    "node_body_span",
]
