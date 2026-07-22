"""DUP001/DUP002 pure rule functions (docs/modules/dup.md's Gate integration).

Both take an already-computed `CloneReport` (from `find_clones(snapshot,
cfg, diff)`) plus the `touched` symref set that produced it, and are pure:
no IO, no snapshot re-walk, just a filter-and-format pass -- matching every
other gate rule in `frob.gates` (`drift_gate`, `fuzz_gate`, ...). The caller
(`frob.gates.__init__`) owns loading `DupConfig`, calling `find_clones`, and
composing these into the gate's `Violation` tuple.
"""

from __future__ import annotations

from frob.dup._models import ClonePair, CloneRegion, CloneReport, CloneTemplate
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)


def _ref_path(ref: str) -> str:
    """The file half of a `path::qualname` symref."""
    return ref.split("::", 1)[0]


def _ref_line(span: tuple[int, int]) -> int:
    """The 1-based line to attribute a violation to: the region's start."""
    return span[0]


def _waiver_hint(rule: str) -> str:
    """The waiver-form suffix every DUP violation message ends with."""
    return f'waive with: frob:waive {rule} reason="..."'


def _extraction_hint(template: CloneTemplate | None) -> str:
    """DUP001's message suffix naming the synthesized extraction, or "" if none.

    `None` means `build_group_template` could not produce a meaningful
    generalization for this group (docs/modules/dup.md's "Reverse-
    templating report" section) -- DUP001 falls back to naming only the
    similarity/rung in that case, same as before this ticket.
    """
    if template is None:
        return ""
    return f"; candidate extraction: {template.suggested_signature}"


# frob:waive DUP001 reason="dup grouped this gate-message builder with \
# deploy/_generate.py's shell-heredoc blocks and _waive.py::_stale_detail \
# purely on generic f-string shape; unrelated domain (DUP001's own \
# violation message), false positive -- ironic given the rule id, but a \
# real structural coincidence"
def _dup001_message(
    new_side: CloneRegion,
    old_side: CloneRegion,
    pair: ClonePair,
    template: CloneTemplate | None,
) -> str:
    """DUP001's full message: sides, similarity/rung, extraction hint, waiver form."""
    return (
        f"{new_side.ref} duplicates pre-existing {old_side.ref} "
        f"({pair.similarity:.0%} similar, rung={pair.rung})"
        f"{_extraction_hint(template)}; "
        f"extract into a shared helper or {_waiver_hint('DUP001')}"
    )


# frob:doc docs/modules/dup.md#gate-integration
# frob:doc docs/guides/extending/dup-detector-registry.md#dup-detector-registry
# frob:enforces ACC-2-1-DUPLICATED-CODE
# frob:enforces CHK-GATE-DUP001
def DUP001(
    report: CloneReport, touched: frozenset[str], threshold: float
) -> tuple[Violation, ...]:
    """A touched symbol clones a PRE-EXISTING (untouched) one at/above threshold.

    Error severity: the diff introduces a duplicate of something that
    already existed before it, which is exactly what "extract into a
    shared helper" fixes. The message names the suggested extraction
    signature when the group's reverse-templating report succeeded
    (`CloneMatchGroup.template`) -- the violation hands the fix, not just
    a percentage, per docs/modules/dup-sota-survey.md sec 4.
    """
    violations: list[Violation] = []
    for group in report.groups:
        for pair in group.pairs:
            new_side, old_side = _new_and_old_side(pair, touched)
            if new_side is None or old_side is None:
                continue
            if pair.similarity < threshold:
                continue
            violations.append(
                Violation(
                    rule="DUP001",
                    severity=Severity.ERROR,
                    file=_ref_path(new_side.ref),
                    line=_ref_line(new_side.span),
                    message=_dup001_message(new_side, old_side, pair, group.template),
                )
            )
    _log.info("DUP001: %d violation(s)", len(violations))
    return tuple(violations)


# frob:doc docs/modules/dup.md#gate-integration
# frob:waive TEST005 reason="DUP002 77.8% branch cover, debt T-0160"
# frob:enforces CHK-GATE-DUP002
def DUP002(
    report: CloneReport, touched: frozenset[str], threshold: float
) -> tuple[Violation, ...]:
    """Two symbols BOTH introduced by the diff clone each other at/above threshold.

    Warn severity: two new copies inside one diff, no pre-existing symbol
    to point at yet -- still worth flagging before it becomes a DUP001 for
    whoever touches either copy next.
    """
    violations: list[Violation] = []
    for group in report.groups:
        for pair in group.pairs:
            if pair.left.ref not in touched or pair.right.ref not in touched:
                continue
            if pair.similarity < threshold:
                continue
            violations.append(
                Violation(
                    rule="DUP002",
                    severity=Severity.WARN,
                    file=_ref_path(pair.left.ref),
                    line=_ref_line(pair.left.span),
                    message=(
                        f"{pair.left.ref} duplicates {pair.right.ref}, both new in "
                        f"this diff ({pair.similarity:.0%} similar, rung={pair.rung}); "
                        f"extract into a shared helper or {_waiver_hint('DUP002')}"
                    ),
                )
            )
    _log.info("DUP002: %d violation(s)", len(violations))
    return tuple(violations)


def _new_and_old_side(
    pair: ClonePair, touched: frozenset[str]
) -> tuple[None, None] | tuple[CloneRegion, CloneRegion]:
    """Split `pair` into (new, old) when exactly one side is touched, else None pair."""
    left_touched = pair.left.ref in touched
    right_touched = pair.right.ref in touched
    if left_touched and not right_touched:
        return pair.left, pair.right
    if right_touched and not left_touched:
        return pair.right, pair.left
    return None, None


__all__ = ["DUP001", "DUP002"]
