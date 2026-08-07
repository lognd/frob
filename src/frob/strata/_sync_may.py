"""`frob.strata._sync_may` -- SYS100-core auto-fix writer (T-1531).

Mirrors `_sync_interface.py`'s own strategy (measure via the SAME check
the gate itself runs, edit `.strata` text in place, never a full
re-serialize) for the SYS100 sibling of that module's SYS104 problem: once
SYS100's core case (net/fs-write/exec) joins per-FILE against a node's
declared `may "<kind>" via [...]` grants (`_effects.py::
_declared_kinds_for_file`, T-1440), adding a new file under an
already-`code=`-bound node that exercises an already-granted capability
kind needs a `may ... via` edit every single time -- the exact hand-patch
`_sync_interface.py`'s own module docstring already documents main going
red over for `interface=`.

Scope, deliberately narrow (T-1531 Done report discloses this cut): only
SYS100's CORE case (`check_capability_conformance`'s THREAT004 delegate,
which carries a real `file`/`kind`/`component` per violation) is handled
here. SYS100's EXTENDED case (eval/process-control/ffi/install-hook/...,
`_selfconform.py::_extended_kind_violations`) fires per-NODE with no
per-file evidence at all -- there is no single file this writer could add
to a `via` list without guessing which of a node's many bound files
actually exercises the capability, so it is left for a follow-up ticket
(T-1137's own never-guess-at-a-fix posture) rather than approximated here.

Grammar (unchanged by this module -- `design/frob.strata` already writes
it by hand today, `strata-core`'s `parse_attrval`/grant grammar, T-1440):
one `may "<kind>" via "<glob-1>", "<glob-2>", ...;` line per grant, or a
bare `may "<kind>";` (no `via`) for a whole-node grant. This module only
ever WIDENS an existing `via` list (sorted union) or INSERTS a brand-new
via-scoped grant line -- it never touches a via-less grant (already covers
every file, so `check_capability_conformance` cannot have fired for it in
the first place) and never removes anything (that is SYS101's own,
separate, deliberately-not-auto-fixed direction -- module docstring's
"never guess" posture applies doubly to narrowing an existing grant)."""
# frob:ticket T-1531

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._effects import check_capability_conformance
from ._errors import StrataError
from ._selfconform import _bind_conformance_inputs, _sorted_capability_files
from ._sync_interface import _NODE_HEADER_RE, _node_body_span
from ._sysdoc import merge_models

_log = get_logger(__name__)

#: One `may "<kind>";` or `may "<kind>" via "<f1>", "<f2>";` grant line --
#: matches both the via-less (whole-node) and via-scoped forms this module
#: reads; only the via-scoped form is ever rewritten (module docstring).
# frob:ticket T-1531
_MAY_LINE_RE = re.compile(
    r'^(?P<indent>[ \t]*)may "(?P<kind>[^"]+)"'
    r'(?:\s+via\s+(?P<via>"[^"]*"(?:\s*,\s*"[^"]*")*))?;\s*$'
)

#: One quoted glob inside a `via "a", "b"` list.
# frob:ticket T-1531
_VIA_ITEM_RE = re.compile(r'"([^"]*)"')


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class MayGrantDiff:
    """One node's `may "<kind>" via [...]` grant widened (`added_files`
    are the newly-added glob entries, sorted) or newly created
    (`created=True`, `added_files` is the grant's whole starting set)."""

    node: str
    kind: str
    added_files: tuple[str, ...]
    created: bool


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class FileMaySyncResult:
    """One `.strata` file's may-grant sync outcome: every widened/created
    grant in it (`diffs`, possibly empty) and the corrected text
    (`new_text`, identical to `old_text` when `diffs` is empty)."""

    path: str
    old_text: str
    new_text: str
    diffs: tuple[MayGrantDiff, ...]

    # frob:ticket T-1531
    # frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
    @property
    def changed(self) -> bool:
        """Whether this file's text actually differs -- mirrors
        `FileSyncResult.changed` (`_sync_interface.py`)."""
        return self.new_text != self.old_text


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class SyncMayReport:
    """Every loaded `.strata` file's may-grant sync outcome, in load order."""

    files: tuple[FileMaySyncResult, ...]

    # frob:ticket T-1531
    # frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
    # frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_widens_existing_via_list  # noqa: E501
    @property
    def has_drift(self) -> bool:
        """True if ANY file in this report needs a rewrite."""
        return any(f.changed for f in self.files)


# frob:ticket T-1531
def _via_names(via_group: str | None) -> list[str]:
    """The quoted glob entries inside a matched `via "..."` group, or an
    empty list when the grant declared no `via` at all (bare `may
    "kind";`)."""
    if via_group is None:
        return []
    return _VIA_ITEM_RE.findall(via_group)


# frob:ticket T-1531
def _render_via_line(indent: str, kind: str, files: frozenset[str]) -> str:
    """Render one `may "<kind>" via "<f1>", "<f2>";` line, sorted for a
    deterministic diff -- mirrors `_render_interface_block`'s sorting
    convention in `_sync_interface.py`."""
    quoted = ", ".join(f'"{f}"' for f in sorted(files))
    return f'{indent}may "{kind}" via {quoted};'


# frob:ticket T-1531
def _sync_one_file_may(
    text: str, additions: dict[str, dict[str, frozenset[str]]]
) -> FileMaySyncResult | None:
    """Widen/insert every `may` grant `additions` names for a node header
    found in `text`; returns `None` when `text` declares no node headers
    at all. `additions` maps node id -> capability kind -> the FULL sorted
    file set that kind's grant must cover (existing via entries already
    unioned in by the caller, `sync_may_report`) -- this function only
    ever compares against what is ALREADY on disk and writes the union,
    never drops an existing entry `additions` did not ask about."""
    lines = text.splitlines()
    header_idxs = [i for i, line in enumerate(lines) if _NODE_HEADER_RE.match(line)]
    if not header_idxs:
        return None
    diffs: list[MayGrantDiff] = []
    offset = 0
    for header_idx in header_idxs:
        idx = header_idx + offset
        header_match = _NODE_HEADER_RE.match(lines[idx])
        if header_match is None:
            continue  # defensive: should always still match post-shift
        node_id = header_match.group("id")
        node_additions = additions.get(node_id)
        if not node_additions:
            continue
        close_idx = _node_body_span(lines, idx)
        before_len = len(lines)
        lines, node_diffs = _rewrite_node_may_grants(
            lines, idx, close_idx, node_id, node_additions
        )
        diffs.extend(node_diffs)
        offset += len(lines) - before_len
    if not diffs:
        return None
    new_text = "\n".join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return FileMaySyncResult(
        path="", old_text=text, new_text=new_text, diffs=tuple(diffs)
    )


# frob:ticket T-1531
def _widen_existing_may_grants(
    lines: list[str],
    header_idx: int,
    close_idx: int,
    node_id: str,
    remaining: dict[str, frozenset[str]],
) -> tuple[int, str | None, list[MayGrantDiff]]:
    """The scan half of `_rewrite_node_may_grants` (ARCH001 split): walk
    `lines[header_idx+1:close_idx]`, widening any EXISTING `may "<kind>"
    via [...]` line whose kind is in `remaining` (popping it out as it is
    handled) and skipping every via-less or already-covering grant
    untouched. Mutates `lines` in place. Returns the index of the LAST
    grant line seen (or `header_idx` if none), that line's indent (or
    `None`), and the diffs actually made -- `_rewrite_node_may_grants`
    uses the first two to anchor a brand-new grant insertion for whatever
    is still left in `remaining` after this call."""
    diffs: list[MayGrantDiff] = []
    insert_after = header_idx
    indent: str | None = None
    idx = header_idx + 1
    while idx < close_idx and remaining:
        m = _MAY_LINE_RE.match(lines[idx])
        if m is None:
            idx += 1
            continue
        indent = m.group("indent")
        insert_after = idx
        kind = m.group("kind")
        want = remaining.pop(kind, None)
        if want is None:
            idx += 1
            continue
        if m.group("via") is None:
            # A via-less grant already covers every file for this kind --
            # `check_capability_conformance` cannot have fired here, so
            # nothing to widen (module docstring's never-narrow posture:
            # this branch is defensive, not expected to trigger).
            idx += 1
            continue
        have = frozenset(_via_names(m.group("via")))
        # frob:waive PERF004 reason="each kind's want/have sets are distinct small \
        # per-grant diffs, not a repeated identical query -- same posture \
        # _sync_interface.py's own PERF002 waiver on its brace-depth scan documents"
        added = tuple(sorted(want - have))
        if not added:
            idx += 1
            continue
        lines[idx] = _render_via_line(indent, kind, have | want)
        diffs.append(
            MayGrantDiff(node=node_id, kind=kind, added_files=added, created=False)
        )
        idx += 1
    return insert_after, indent, diffs


# frob:ticket T-1531
def _insert_new_may_grants(
    lines: list[str],
    header_idx: int,
    insert_after: int,
    indent: str | None,
    node_id: str,
    remaining: dict[str, frozenset[str]],
) -> tuple[list[str], list[MayGrantDiff]]:
    """The insert half of `_rewrite_node_may_grants` (ARCH001 split):
    everything still in `remaining` after `_widen_existing_may_grants`
    has no existing `may "<kind>"` line at all for this node -- insert a
    brand-new via-scoped grant right after the last grant seen
    (`insert_after`, or the header itself if this node declares none
    yet), same "no established position, insert right after the anchor"
    convention `_rewrite_node_interface_block` uses. A no-op (returns
    `lines` unchanged, empty diffs) when `remaining` is already empty."""
    if not remaining:
        return lines, []
    header_match = _NODE_HEADER_RE.match(lines[header_idx])
    assert header_match is not None
    line_indent = (
        indent if indent is not None else header_match.group("indent") + "    "
    )
    new_lines = [
        _render_via_line(line_indent, kind, files)
        for kind, files in sorted(remaining.items())
    ]
    diffs = [
        MayGrantDiff(
            node=node_id,
            kind=kind,
            added_files=tuple(sorted(remaining[kind])),
            created=True,
        )
        for kind in sorted(remaining)
    ]
    new_lines_full = lines[: insert_after + 1] + new_lines + lines[insert_after + 1 :]
    return new_lines_full, diffs


# frob:ticket T-1531
def _rewrite_node_may_grants(
    lines: list[str],
    header_idx: int,
    close_idx: int,
    node_id: str,
    node_additions: dict[str, frozenset[str]],
) -> tuple[list[str], list[MayGrantDiff]]:
    """Widen/insert one node's `may "<kind>" via [...]` grants for every
    kind in `node_additions`, split out of `_sync_one_file_may` to keep
    its loop nest short (ARCH001, T-1535: further split into
    `_widen_existing_may_grants`/`_insert_new_may_grants`). Returns the
    (possibly rewritten) full `lines` list plus the diffs actually made."""
    remaining = dict(node_additions)
    insert_after, indent, widen_diffs = _widen_existing_may_grants(
        lines, header_idx, close_idx, node_id, remaining
    )
    new_lines, insert_diffs = _insert_new_may_grants(
        lines, header_idx, insert_after, indent, node_id, remaining
    )
    return new_lines, widen_diffs + insert_diffs


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_no_drift_reports_clean  # noqa: E501
# frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_widens_existing_via_list  # noqa: E501
# frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_inserts_new_grant_when_none_declared  # noqa: E501
def sync_may_report(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[SyncMayReport, StrataError]:
    """Load+merge every `.strata` file under `root/design_dir`, bind code
    (the `_capability_binding` superset SYS100 core itself uses), and
    compute every SYS100-core violation's node/kind/file as a `may`
    grant-widening (or brand-new-grant) diff. Never writes --
    `apply_sync_may` is the only function in this module with a side
    effect."""
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        first = ids.errors[0]
        _log.error("sync_may_report: %s failed to load: %s", first.path, first.error)
        return Err(first.error)
    if not ids.models:
        _log.info("sync_may_report: no design models under %s/%s", root, design_dir)
        return Ok(SyncMayReport(files=()))

    model = merge_models(ids.models)
    capability_files = _sorted_capability_files(root)
    bound = _bind_conformance_inputs(model, root, capability_files)
    if bound.is_err:
        _log.error("sync_may_report: binding failed: %s", bound.danger_err)
        return Err(bound.danger_err)
    binding = bound.danger_ok

    conformance = check_capability_conformance(model, binding, root)
    additions: dict[str, dict[str, set[str]]] = {}
    for violation in conformance.violations:
        by_kind = additions.setdefault(violation.component, {})
        by_kind.setdefault(violation.kind, set()).add(violation.file)
    if not additions:
        return Ok(SyncMayReport(files=()))
    frozen_additions = {
        node: {kind: frozenset(files) for kind, files in by_kind.items()}
        for node, by_kind in additions.items()
    }

    design_root = root / design_dir
    results: list[FileMaySyncResult] = []
    # frob:waive WALK001 reason="design_root (e.g. design/) is a small, hand-authored \
    # .strata source subtree with no nested .git/.venv/node_modules/build/dist/target \
    # to prune -- excludes.walk_pruned would add a filter that never fires here, not \
    # change behavior, same posture _sync_interface.py's own WALK001 waiver documents"
    for path in sorted(design_root.rglob("*.strata")):
        text = path.read_text(encoding="utf-8")
        if "node " not in text and "store " not in text:
            continue
        result = _sync_one_file_may(text, frozen_additions)
        if result is None:
            continue
        rel = path.relative_to(root).as_posix()
        results.append(
            FileMaySyncResult(
                path=rel,
                old_text=result.old_text,
                new_text=result.new_text,
                diffs=result.diffs,
            )
        )
    drifted = sum(1 for r in results if r.changed)
    _log.info("sync_may_report: %d file(s) scanned, %d drifted", len(results), drifted)
    return Ok(SyncMayReport(files=tuple(results)))


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/unit/strata/test_sync_may.py::TestApplySyncMay.test_writes_only_changed_files  # noqa: E501
def apply_sync_may(root: Path, report: SyncMayReport) -> tuple[str, ...]:
    """Write every changed `FileMaySyncResult.new_text` in `report` back to
    its file, in the same load order; returns the sorted repo-relative
    paths actually rewritten. Mirrors `apply_sync_interface`'s own
    write-only-what-changed contract."""
    from frob.tickets._store import atomic_write

    written: list[str] = []
    for result in report.files:
        if not result.changed:
            continue
        write_result = atomic_write(root / result.path, result.new_text)
        if write_result.is_err:
            _log.error(
                "apply_sync_may: write to %s failed, original left untouched: %s",
                result.path,
                write_result.danger_err,
            )
            continue
        written.append(result.path)
    return tuple(sorted(written))


__all__ = [
    "FileMaySyncResult",
    "MayGrantDiff",
    "SyncMayReport",
    "apply_sync_may",
    "sync_may_report",
]
