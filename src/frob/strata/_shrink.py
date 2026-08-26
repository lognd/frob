"""frob.strata._shrink -- SYS101 shrink-only auto-tightening writer (T-2923,
child of epic T-2920).

`may=` is a CEILING on what a node's code is permitted to do; `frob sys
shrink` is the ONLY direction in which any code in this repo may ever
write that ceiling: dropping a capability atom a node declares but the
scanner never observes anywhere in that node's own `code=`-bound files
(SYS101, `frob.strata._selfconform_ids.SYS_STALE_DESIGN`). This module
contains no branch that ADDS, WIDENS, or otherwise increases any node's
declared capability surface -- there is no flag, env var, or config key
on `shrink_report`/`apply_shrink` that reaches one, by construction
(`tests/unit/strata/test_shrink.py::TestNoWideningPath` asserts this
against the actual module surface, not by inspection alone).

T-2920 (parent epic, read its own ticket body for the full design):
regenerating a ceiling FROM observation (the T-2907 proposal this program
dropped) makes it equal whatever the code happens to do -- a rubber
stamp. Only the LOOSE direction (declared, never observed) is safe to
auto-tighten; the TIGHT direction (observed, never declared -- capability
escalation, SYS100) must never be auto-synced under any flag, and stays a
hard error everywhere in this repo's gates. `frob.strata._sync_may`
already ships the exact widening machinery T-2920 forbids (SYS100's
`sync_may_report`/`apply_sync_may`, `sync_may_extended_report`/
`apply_sync_may_extended`, T-1531/T-1545) -- deliberately DIFFERENT
policy, explicitly reversed by T-2920 on the user's own instruction, not
an accident or an oversight. T-2922 (blocks T-2920) unwires that
module's caller in `frob.gates._fix_engine_sync`; this module does not
touch `_sync_may.py` at all, and `_sync_may.py`'s widening functions stay
physically in place, untouched, pending T-2922's own closing step (do
not delete them here -- that would break T-2922's caller with an
ImportError before that ticket lands).

A capability-bearing file no node's `code=` glob binds (SYS103) is a
THIRD case this module deliberately never touches: `shrink_report` never
invents a new `via` binding for an unbound file, because doing so would
erase precisely the signal that a new, uncategorised, capability-bearing
file entered the system. SYS103 has no matching rewrite path here at
all -- there is nothing for `frob sys shrink` to do about it but leave it
as the error it already is.

Conservative-by-construction for a partially-stale kind: SYS101 fires
PER (kind, via) pair (`frob.strata._selfconform_core_rules
._stale_design_violations_for_node`), so a node can declare the SAME
kind via two different `via` scopes where only one is stale. Re-deriving
that per-via join here would duplicate `_selfconform`'s own logic and
risk drifting from it (the exact class of bug T-2920's own cover letter
warns about generally). Instead, this module counts how many `may
"<kind>"` grant LINES a node's `.strata` text actually declares for a
kind against how many SYS101 findings `check_self_conformance` reported
for that same (node, kind): only when every declared instance of that
kind is stale does this module drop them; a partially-stale kind is left
untouched entirely, logged at INFO, for a human to narrow by hand -- the
same "never guess" posture `_sync_may.py`'s own module docstring already
states for narrowing an existing grant."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._errors import StrataError
from ._selfconform import check_self_conformance
from ._selfconform_ids import SYS_STALE_DESIGN
from ._sync_may import node_body_span
from ._sysdoc import merge_models

_log = get_logger(__name__)

#: One node OR store header line -- identical shape to `_sync_may.py`'s own
#: `_NODE_HEADER_RE` (module docstring there explains why the parser/
#: elaborator is never used to regenerate this file's text: it would lose
#: comments). Kept as a separate copy rather than importing the private
#: name across modules for one regex, matching this repo's own DUP001
#: tolerance for a single-pattern near-duplicate versus a shared-module
#: extraction that would need its own home for one regex.
_NODE_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:node|store)\s+(?P<id>\S+)\b[^{]*\{\s*$"
)

#: One `may "<kind>";` or `may "<kind>" via "<f1>", "<f2>";` grant line --
#: identical shape to `_sync_may.py::_MAY_LINE_RE`, kept local for the same
#: reason as `_NODE_HEADER_RE` above.
_MAY_LINE_RE = re.compile(
    r'^(?P<indent>[ \t]*)may "(?P<kind>[^"]+)"'
    r'(?:\s+via\s+(?P<via>"[^"]*"(?:\s*,\s*"[^"]*")*))?;\s*$'
)


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_drops_declared_but_never_observed_capability kind="unit"  # noqa: E501
@dataclass(frozen=True)
class ShrinkDrop:
    """One `may "<kind>";` grant line removed from `node` because
    `check_self_conformance`'s own SYS101 join found EVERY declared
    instance of that kind on that node stale (declared, never
    observed)."""

    node: str
    kind: str


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_partially_stale_kind_is_left_untouched kind="unit"  # noqa: E501
@dataclass(frozen=True)
class PartialStaleSkip:
    """One (node, kind) `shrink_report` deliberately left UNTOUCHED: some
    but not all of that kind's declared grant instances (distinct `via`
    scopes) are stale. Narrowing correctly needs the per-via join
    `frob.strata._selfconform_core_rules._stale_design_violations_for_node`
    already computes internally; re-deriving it here risks drifting from
    that single source of truth (module docstring), so this module skips
    rather than guesses."""

    node: str
    kind: str
    stale_instances: int
    declared_instances: int


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_apply_shrink_writes_only_changed_files kind="unit"  # noqa: E501
@dataclass(frozen=True)
class FileShrinkResult:
    """One `.strata` file's shrink outcome: every dropped grant in it
    (`drops`, possibly empty) and the corrected text (`new_text`,
    identical to `old_text` when `drops` is empty)."""

    path: str
    old_text: str
    new_text: str
    drops: tuple[ShrinkDrop, ...]

    # frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
    # frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_apply_shrink_writes_only_changed_files kind="unit"  # noqa: E501
    @property
    def changed(self) -> bool:
        """Whether this file's text actually differs from what was read."""
        return self.new_text != self.old_text


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_no_drift_when_everything_observed kind="unit"  # noqa: E501
@dataclass(frozen=True)
class ShrinkReport:
    """Every loaded `.strata` file's shrink outcome, in load order, plus
    every (node, kind) left untouched because it was only partially
    stale."""

    files: tuple[FileShrinkResult, ...]
    skipped: tuple[PartialStaleSkip, ...] = ()

    # frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
    # frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_no_drift_when_everything_observed kind="unit"  # noqa: E501
    @property
    def has_drift(self) -> bool:
        """True if ANY file in this report needs a rewrite."""
        return any(f.changed for f in self.files)


def _stale_counts_by_node_kind(violations) -> dict[tuple[str, str], int]:  # noqa: ANN001
    """`{(node, kind): stale_instance_count}` over every SYS101 finding in
    `violations` -- `check_self_conformance`'s own report is the single
    source of truth for "this instance is stale"; this function only
    tallies it, never re-derives it."""
    counts: dict[tuple[str, str], int] = {}
    for v in violations:
        if v.rule != SYS_STALE_DESIGN or v.capability is None:
            continue
        key = (v.node, v.capability)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _drop_stale_grants_in_node(
    lines: list[str],
    header_idx: int,
    node_id: str,
    stale_counts: dict[tuple[str, str], int],
    keep: list[bool],
) -> tuple[list[ShrinkDrop], list[PartialStaleSkip]]:
    """One node's share of `_drop_stale_grants_in_file` (ARCH001 split,
    T-2923): count each declared kind's grant LINES within this node's
    own body span against `stale_counts[(node, kind)]`, mutating `keep`
    in place for every line whose kind is FULLY stale. Returns the drops
    and skips made for this node alone."""
    close_idx = node_body_span(lines, header_idx)
    # frob:waive PERF004 reason="one small per-node scan of its own body span, not a \
    # repeated identical query"
    lines_by_kind: dict[str, list[int]] = {}
    for idx in range(header_idx + 1, close_idx):
        m = _MAY_LINE_RE.match(lines[idx])
        if m is None:
            continue
        lines_by_kind.setdefault(m.group("kind"), []).append(idx)
    drops: list[ShrinkDrop] = []
    skips: list[PartialStaleSkip] = []
    for kind, idxs in sorted(lines_by_kind.items()):
        stale = stale_counts.get((node_id, kind), 0)
        if stale == 0:
            continue  # not stale at all -- nothing to do
        if stale < len(idxs):
            skips.append(
                PartialStaleSkip(
                    node=node_id,
                    kind=kind,
                    stale_instances=stale,
                    declared_instances=len(idxs),
                )
            )
            _log.info(
                "shrink: %s kind=%r on node=%s is only partially stale "
                "(%d of %d declared instances) -- left untouched, narrow "
                "by hand",
                SYS_STALE_DESIGN,
                kind,
                node_id,
                stale,
                len(idxs),
            )
            continue
        for idx in idxs:
            keep[idx] = False
        drops.append(ShrinkDrop(node=node_id, kind=kind))
        _log.info(
            "shrink: dropping %s kind=%r from node=%s (%d declared "
            "instance(s), all stale)",
            SYS_STALE_DESIGN,
            kind,
            node_id,
            len(idxs),
        )
    return drops, skips


def _drop_stale_grants_in_file(
    text: str, stale_counts: dict[tuple[str, str], int]
) -> tuple[FileShrinkResult | None, list[PartialStaleSkip]]:
    """One `.strata` file's shrink pass: for every node header found in
    `text`, delegate to `_drop_stale_grants_in_node` (ARCH001 split) to
    decide which of that node's grant lines are fully stale."""
    lines = text.splitlines()
    header_idxs = [i for i, line in enumerate(lines) if _NODE_HEADER_RE.match(line)]
    if not header_idxs:
        return None, []
    keep = [True] * len(lines)
    drops: list[ShrinkDrop] = []
    skips: list[PartialStaleSkip] = []
    for header_idx in header_idxs:
        header_match = _NODE_HEADER_RE.match(lines[header_idx])
        if header_match is None:
            continue  # defensive: should always still match
        node_drops, node_skips = _drop_stale_grants_in_node(
            lines, header_idx, header_match.group("id"), stale_counts, keep
        )
        drops.extend(node_drops)
        skips.extend(node_skips)
    if not drops:
        return None, skips
    new_lines = [line for line, k in zip(lines, keep, strict=True) if k]
    new_text = "\n".join(new_lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return (
        FileShrinkResult(path="", old_text=text, new_text=new_text, drops=tuple(drops)),
        skips,
    )


def _shrink_scan_design_root(
    root: Path, design_root: Path, stale_counts: dict[tuple[str, str], int]
) -> ShrinkReport:
    """`shrink_report`'s own file-walk half (ARCH001 split, T-2923): scan
    every `.strata` file under `design_root`, drop each fully-stale grant
    via `_drop_stale_grants_in_file`, and fold the per-file results into
    one `ShrinkReport`."""
    results: list[FileShrinkResult] = []
    all_skips: list[PartialStaleSkip] = []
    # frob:waive WALK001 reason="design_root is a small, hand-authored .strata source \
    # subtree with no nested .git/.venv/node_modules/build/dist/target to prune -- \
    # same posture _sync_may.py's own sync_may_report documents for the identical walk"
    for path in sorted(design_root.rglob("*.strata")):
        text = path.read_text(encoding="utf-8")
        if "node " not in text and "store " not in text:
            continue
        result, skips = _drop_stale_grants_in_file(text, stale_counts)
        all_skips.extend(skips)
        if result is None:
            continue
        rel = path.relative_to(root).as_posix()
        results.append(
            FileShrinkResult(
                path=rel,
                old_text=result.old_text,
                new_text=result.new_text,
                drops=result.drops,
            )
        )
    drifted = sum(1 for r in results if r.changed)
    _log.info(
        "shrink_report: %d file(s) scanned, %d drifted, %d kind(s) left "
        "partially stale",
        len(results),
        drifted,
        len(all_skips),
    )
    return ShrinkReport(files=tuple(results), skipped=tuple(all_skips))


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_drops_declared_but_never_observed_capability kind="unit"  # noqa: E501
def shrink_report(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[ShrinkReport, StrataError]:
    """Load+merge every `.strata` file under `root/design_dir`, run
    `check_self_conformance` (the SAME join `frob sys audit` itself
    trusts) to find every SYS101 declared-but-never-observed instance,
    then delegate to `_shrink_scan_design_root` to drop each fully-stale
    (kind, node) grant from its owning file's text. Never writes --
    `apply_shrink` is the only function in this module with a side
    effect, matching `_sync_may.sync_may_report`'s own read/write
    split."""
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        first = ids.errors[0]
        _log.error("shrink_report: %s failed to load: %s", first.path, first.error)
        return Err(first.error)
    if not ids.models:
        _log.info("shrink_report: no design models under %s/%s", root, design_dir)
        return Ok(ShrinkReport(files=()))

    model = merge_models(ids.models)
    conformance = check_self_conformance(model, root)
    if conformance.is_err:
        _log.error(
            "shrink_report: check_self_conformance failed: %s",
            conformance.danger_err,
        )
        return Err(conformance.danger_err)

    stale_counts = _stale_counts_by_node_kind(conformance.danger_ok.violations)
    if not stale_counts:
        _log.info("shrink_report: no SYS101 (declared-but-never-observed) findings")
        return Ok(ShrinkReport(files=()))

    return Ok(_shrink_scan_design_root(root, root / design_dir, stale_counts))


# frob:doc docs/commands/sys.md#frob-sys-shrink-t-2923
# frob:tests tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants.test_apply_shrink_writes_only_changed_files kind="unit"  # noqa: E501
def apply_shrink(root: Path, report: ShrinkReport) -> tuple[str, ...]:
    """Write every `report.files` entry whose text actually changed back
    to disk; returns the relative paths written, in report order. Mirrors
    `_sync_may.py::apply_sync_may`'s own write loop exactly, minus the
    parts specific to its two report kinds."""
    written: list[str] = []
    for f in report.files:
        if not f.changed:
            continue
        (root / f.path).write_text(f.new_text, encoding="utf-8")
        written.append(f.path)
    if written:
        _log.info("apply_shrink: wrote %d file(s): %s", len(written), written)
    return tuple(written)
