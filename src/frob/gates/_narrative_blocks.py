"""NARR001: an over-long `# T-####:` narrative comment block in code or
`.strata` design source (docs/modules/gates.md#rule-catalog, T-2993).

T-2994's doctrine: code carries UTILITY (what a reader about to modify or
reuse this needs to know); tickets carry NARRATIVE (why we arrived here,
what a prior attempt got wrong, which policy superseded which). A
`# T-####: ...` comment block that runs long is usually doing the second
job in the first place -- the ticket it names already owns that story.

This gate is intentionally NOT a "does this block mention a ticket"
lexical ban -- a short block that explains something load-bearing about
the code (T-2993's own `_socketd.py`/T-2961 example: "a CLASS statement
referencing a missing base at module scope raises AttributeError at
IMPORT time, not when the daemon is used, unlike the fcntl/msvcrt pattern
used for FUNCTIONS") is exactly the KEEP case and must stay quiet. The
signal used here is LENGTH past a threshold, not the presence of a T-id:
T-2994's own doctrine says the split is a judgement a human/agent makes
per block, not something this detector can resolve unattended -- so it
flags candidates for a `frob narrative move` review, it does not decide
FOR the reader which lines are archaeology.

Ships at WARN (T-2993 acceptance): the existing 1,728 blocks are a burn-
down, not a day-one failure. Promote to ERROR only after that burn-down,
mirroring the TICK011/T-2372 WARN-then-ERROR precedent this gate's own
docstring cites by name.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["NARR001_THRESHOLD_LINES", "narrative_blocks_gate", "scan_narrative_blocks"]

# A block longer than this many comment lines is a candidate for
# migration. Chosen above the owner's own KEEP example (the _socketd.py
# T-2961 block's load-bearing sentence is 4-5 lines) and well below the
# largest measured offenders (105-130 lines) so the must-fire/must-stay-
# quiet fixtures both land clearly on either side of it.
# frob:doc docs/commands/narrative.md#narr001-the-detector
NARR001_THRESHOLD_LINES = 12

_TICKET_LEAD_RE = re.compile(r"^\s*#\s*T-\d{2,6}\s*:")
_COMMENT_LINE_RE = re.compile(r"^\s*#")
_SCANNED_SUFFIXES = (".py", ".strata")


def _iter_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Contiguous `(start, end)` 0-indexed line ranges (inclusive) of
    comment blocks that OPEN with a `# T-####:` lead line -- the shape
    T-2993 measured (a leading ticket-id line, followed by zero or more
    plain `#` continuation lines with no blank-line break)."""
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if _TICKET_LEAD_RE.match(lines[i]):
            start = i
            j = i + 1
            while j < n and _COMMENT_LINE_RE.match(lines[j]):
                j += 1
            blocks.append((start, j - 1))
            i = j
        else:
            i += 1
    return blocks


# frob:doc docs/commands/narrative.md#narr001-the-detector
# frob:tests \
# tests/test_narrative_blocks.py::TestNarrativeBlocksGate.test_must_fire_long_archaeolo\
# gy_block
# frob:tests \
# tests/test_narrative_blocks.py::TestNarrativeBlocksGate.test_must_stay_quiet_short_ke\
# ep_block
# frob:tests \
# tests/test_narrative_blocks.py::TestNarrativeBlocksGate.test_socketd_t2961_block_stay\
# s_quiet_at_default_threshold
# frob:tests \
# tests/test_narrative_blocks.py::TestNarrativeBlocksGate.test_threshold_boundary_is_in\
# clusive
def scan_narrative_blocks(
    path: Path, text: str, *, threshold: int = NARR001_THRESHOLD_LINES
) -> tuple[Violation, ...]:
    """Every `# T-####:`-led comment block in `text` longer than
    `threshold` lines, as `NARR001` violations pointing at the block's
    first line. Pure function of file content -- no filesystem access
    beyond what the caller already did to produce `text` -- so fixtures
    can call this directly without touching disk."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for start, end in _iter_blocks(lines):
        length = end - start + 1
        if length <= threshold:
            continue
        violations.append(
            Violation(
                rule="NARR001",
                severity=Severity.WARN,
                file=str(path),
                line=start + 1,
                message=(
                    f"NARR001: {length}-line ticket-narrative comment block "
                    f"(over the {threshold}-line threshold) -- if this is "
                    "recording WHY/history rather than something a reader "
                    "needs to safely modify or reuse this code, move it "
                    "with `frob narrative move` into the ticket it already "
                    "names, keeping only the load-bearing part in place"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/commands/narrative.md#narr001-the-detector
# frob:tests \
# tests/test_narrative_blocks.py::TestNarrativeBlocksGateRepoScan.test_fires_on_a_track\
# ed_file_with_a_long_block
# frob:waive WIRE001 reason="not yet wired into gates/__init__.py's GATE_RUNNERS dict \
# -- that file was held by T-2986's live in-progress lease for the whole of T-2993's \
# work window (T-2994 scope-realism constraint: do not attempt a repo-wide rewrite or \
# expand scope onto a leased file)" follow_up="T-3014"
def narrative_blocks_gate(root: Path) -> tuple[Violation, ...]:
    """NARR001 over every tracked `.py`/`.strata` file under `root` (T-2993).
    Reads files directly rather than via a shared snapshot object -- this
    gate only needs raw text, no AST -- matching `_exclude_hazard.py`'s own
    lightweight-scan posture for a repo-wide structural check."""
    from frob.gates._tracked_files import tracked_files as _shared_tracked_files

    tracked = _shared_tracked_files(root, caller="narrative_blocks_gate")
    violations: list[Violation] = []
    for rel in tracked:
        if not rel.endswith(_SCANNED_SUFFIXES):
            continue
        full = root / rel
        # frob:waive SELFAUDIT001 reason="fs.read of every tracked .py/.strata file \
        # under root, same repo-wide-scan shape excludehazard/refs/secrets already \
        # declare fs.read for; this gate's own node binding is the T-3014 \
        # follow-up (WIRE001 waiver above), not yet added because design/frob.strata \
        # was T-2986-leased for this ticket's whole work window" \
        # follow_up="T-3014"
        try:
            text = full.read_text(encoding="utf-8")
        except OSError:
            continue
        violations.extend(scan_narrative_blocks(Path(rel), text))
    _log.debug(
        "narrative_blocks: %d NARR001 violation(s) under %s", len(violations), root
    )
    return tuple(violations)
