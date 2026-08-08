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

T-1531 handled only SYS100's CORE case (`check_capability_conformance`'s
THREAT004 delegate, which carries a real `file`/`kind`/`component` per
violation) and left the EXTENDED case (eval/process-control/ffi/
install-hook/sql/deserialize/html_render/fetch_url/client_storage,
`_selfconform.py::_extended_kind_violations`) as a disclosed follow-up
(T-1545): EXTENDED fires per-NODE with no per-file evidence at all, so
there is no single file `sync_may_extended_report` could add to a `via`
list without guessing which of a node's many bound files actually
exercises the capability.

T-1545's resolution: rather than guess a `via` file (T-1137's own
never-guess-at-a-fix posture forbids that), `sync_may_extended_report`
inserts a bare, WHOLE-NODE `may "<kind>";` grant (no `via` at all) for
every EXTENDED-kind capability `_extended_kind_violations` reports as
observed-but-undeclared. A via-less grant covers every file the node
owns, so it is DELIBERATELY the most conservative shape available --
strictly broader than any per-file `via` entry could ever be wrong in
the narrow direction (it can never under-grant relative to what is
actually needed), the same "widen or create, never narrow or guess"
posture `sync_may_report`'s CORE writer already applies, just with no
`via` list to narrow to in the first place. A human reviewing the diff
sees a plain `may "eval";`-style line and can hand-narrow it to a `via`
list later if the false-positive-broad grant is worth tightening; the
auto-fix's job is only to make the declaration truthful (SYS100 stops
firing), not to reverse-engineer which file actually calls `eval`.

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
from typing import TypeAlias

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._effects import check_capability_conformance
from ._errors import StrataError
from ._models import KernelModel
from ._selfconform import (
    _bind_conformance_inputs,
    _extended_kind_violations,
    _observed_extended_kinds_by_node,
    _sorted_capability_files,
)
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
# frob:tests \
# tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_no_drift_reports_clean
# frob:tests \
# tests/unit/strata/test_sync_may.py::TestSyncMayReport.test_widens_existing_via_list
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


_MaySyncResult: TypeAlias = "FileMaySyncResult | FileMayExtendedSyncResult"


def _write_changed_may_files(
    root: Path, results: "tuple[_MaySyncResult, ...]"
) -> tuple[str, ...]:
    """Write every `result.changed` file's `new_text` back to disk, in
    load order; returns the sorted repo-relative paths actually
    rewritten. Shared by `apply_sync_may` (CORE, via-scoped) and
    `apply_sync_may_extended` (T-1545, whole-node bare grants) -- both
    result types carry the same `path`/`new_text`/`changed` shape, only
    their `diffs` element type differs."""
    from frob.tickets._store import atomic_write

    written: list[str] = []
    for result in results:
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


# frob:ticket T-1531
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests \
# tests/unit/strata/test_sync_may.py::TestApplySyncMay.test_writes_only_changed_files
def apply_sync_may(root: Path, report: SyncMayReport) -> tuple[str, ...]:
    """Write every changed `FileMaySyncResult.new_text` in `report` back to
    its file, in the same load order; returns the sorted repo-relative
    paths actually rewritten. Mirrors `apply_sync_interface`'s own
    write-only-what-changed contract."""
    return _write_changed_may_files(root, report.files)


# ---------------------------------------------------------------------------
# SYS100 EXTENDED (T-1545): eval/process-control/ffi/install-hook/sql/
# deserialize/html_render/fetch_url/client_storage -- no per-file evidence,
# so the fix is a deliberately conservative WHOLE-NODE (via-less) grant
# insertion, never a per-file `via` guess (module docstring above).
# ---------------------------------------------------------------------------


# frob:ticket T-1545
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class WholeNodeMayGrantDiff:
    """One node's brand-new, via-less `may "<kind>";` grant inserted by
    `sync_may_extended_report` -- there is no `added_files`/`created`
    distinction here (unlike `MayGrantDiff`): EXTENDED-kind violations
    are by construction always a fresh grant (`_extended_kind_violations`
    only fires when the kind is undeclared in ANY form, bare or
    via-scoped), never a widening of an existing line."""

    node: str
    kind: str


# frob:ticket T-1545
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class FileMayExtendedSyncResult:
    """One `.strata` file's whole-node may-grant sync outcome -- same
    shape as `FileMaySyncResult`, parameterized over `WholeNodeMayGrantDiff`
    instead of `MayGrantDiff`."""

    path: str
    old_text: str
    new_text: str
    diffs: tuple[WholeNodeMayGrantDiff, ...]

    # frob:ticket T-1545
    # frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
    @property
    def changed(self) -> bool:
        """Whether this file's text actually differs -- mirrors
        `FileMaySyncResult.changed`."""
        return self.new_text != self.old_text


# frob:ticket T-1545
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
@dataclass(frozen=True)
class SyncMayExtendedReport:
    """Every loaded `.strata` file's whole-node may-grant sync outcome,
    in load order -- the T-1545 EXTENDED-kind sibling of `SyncMayReport`."""

    files: tuple[FileMayExtendedSyncResult, ...]

    # frob:ticket T-1545
    # frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
    # frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport.test_inserts_whole_node_grant_for_extended_kind  # noqa: E501
    @property
    def has_drift(self) -> bool:
        """True if ANY file in this report needs a rewrite."""
        return any(f.changed for f in self.files)


# frob:ticket T-1545
def _bare_may_line(indent: str, kind: str) -> str:
    """Render one via-less `may "<kind>";` grant line -- the whole-node
    form `_insert_whole_node_may_grants` inserts, mirroring
    `_render_via_line`'s sorting-for-determinism convention (a single
    kind has nothing to sort, but the naming stays parallel)."""
    return f'{indent}may "{kind}";'


# frob:ticket T-1545
def _insert_whole_node_may_grants(
    lines: list[str],
    header_idx: int,
    close_idx: int,
    node_id: str,
    missing_kinds: frozenset[str],
) -> tuple[list[str], list[WholeNodeMayGrantDiff]]:
    """Insert a bare `may "<kind>";` grant for every kind in
    `missing_kinds`, right after the last existing `may` line inside the
    node body (or right after the header if it declares none yet) --
    module docstring's whole-node, never-guess-a-`via` policy. There is
    no widen case here (unlike `_rewrite_node_may_grants`): every kind in
    `missing_kinds` is, by `_extended_kind_violations`'s own contract,
    undeclared in ANY form for this node, so this only ever inserts."""
    if not missing_kinds:
        return lines, []
    insert_after = header_idx
    indent: str | None = None
    for idx in range(header_idx + 1, close_idx):
        m = _MAY_LINE_RE.match(lines[idx])
        if m is not None:
            insert_after = idx
            indent = m.group("indent")
    header_match = _NODE_HEADER_RE.match(lines[header_idx])
    assert header_match is not None
    line_indent = (
        indent if indent is not None else header_match.group("indent") + "    "
    )
    new_lines = [_bare_may_line(line_indent, kind) for kind in sorted(missing_kinds)]
    diffs = [
        WholeNodeMayGrantDiff(node=node_id, kind=kind) for kind in sorted(missing_kinds)
    ]
    full = lines[: insert_after + 1] + new_lines + lines[insert_after + 1 :]
    return full, diffs


# frob:ticket T-1545
def _sync_one_file_may_extended(
    text: str, additions: dict[str, frozenset[str]]
) -> FileMayExtendedSyncResult | None:
    """Insert every whole-node grant `additions` names for a node header
    found in `text`; returns `None` when `text` declares no node headers
    at all. `additions` maps node id -> the set of EXTENDED kinds that
    node is missing entirely -- mirrors `_sync_one_file_may`'s per-header
    walk, calling `_insert_whole_node_may_grants` instead of
    `_rewrite_node_may_grants`."""
    lines = text.splitlines()
    header_idxs = [i for i, line in enumerate(lines) if _NODE_HEADER_RE.match(line)]
    if not header_idxs:
        return None
    diffs: list[WholeNodeMayGrantDiff] = []
    offset = 0
    for header_idx in header_idxs:
        idx = header_idx + offset
        header_match = _NODE_HEADER_RE.match(lines[idx])
        if header_match is None:
            continue  # defensive: should always still match post-shift
        node_id = header_match.group("id")
        missing = additions.get(node_id)
        if not missing:
            continue
        close_idx = _node_body_span(lines, idx)
        before_len = len(lines)
        lines, node_diffs = _insert_whole_node_may_grants(
            lines, idx, close_idx, node_id, missing
        )
        diffs.extend(node_diffs)
        offset += len(lines) - before_len
    if not diffs:
        return None
    new_text = "\n".join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return FileMayExtendedSyncResult(
        path="", old_text=text, new_text=new_text, diffs=tuple(diffs)
    )


# frob:ticket T-1545
def _extended_may_additions(
    model: KernelModel, *, root: Path, capability_files: list[Path]
) -> Result[dict[str, frozenset[str]], StrataError]:
    """Bind code and compute every SYS100-EXTENDED violation's node ->
    missing-kinds set (ARCH001 split from `sync_may_extended_report`'s
    binding/join phase)."""
    bound = _bind_conformance_inputs(model, root, capability_files)
    if bound.is_err:
        _log.error("sync_may_extended_report: binding failed: %s", bound.danger_err)
        return Err(bound.danger_err)
    binding = bound.danger_ok

    observed_by_node = _observed_extended_kinds_by_node(binding, root)
    violations = _extended_kind_violations(model, observed_by_node)
    additions: dict[str, set[str]] = {}
    for violation in violations:
        if violation.capability is None:
            continue
        additions.setdefault(violation.node, set()).add(violation.capability)
    return Ok({node: frozenset(kinds) for node, kinds in additions.items()})


# frob:ticket T-1545
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport.test_no_drift_reports_clean  # noqa: E501
# frob:tests tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport.test_inserts_whole_node_grant_for_extended_kind  # noqa: E501
def sync_may_extended_report(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[SyncMayExtendedReport, StrataError]:
    """T-1545: load+merge every `.strata` file under `root/design_dir`,
    bind code, and compute every SYS100-EXTENDED violation
    (`_selfconform._extended_kind_violations`) as a whole-node, via-less
    `may "<kind>";` grant insertion (module docstring: no per-file
    evidence exists for this case, so the fix cannot narrow to a `via`
    list the way `sync_may_report`'s CORE case does). Never writes --
    `apply_sync_may_extended` is the only function with a side effect."""
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        first = ids.errors[0]
        _log.error(
            "sync_may_extended_report: %s failed to load: %s", first.path, first.error
        )
        return Err(first.error)
    if not ids.models:
        _log.info(
            "sync_may_extended_report: no design models under %s/%s", root, design_dir
        )
        return Ok(SyncMayExtendedReport(files=()))

    model = merge_models(ids.models)
    capability_files = _sorted_capability_files(root)
    additions_result = _extended_may_additions(
        model, root=root, capability_files=capability_files
    )
    if additions_result.is_err:
        return Err(additions_result.danger_err)
    additions = additions_result.danger_ok
    if not additions:
        return Ok(SyncMayExtendedReport(files=()))

    design_root = root / design_dir
    results: list[FileMayExtendedSyncResult] = []
    # frob:waive WALK001 reason="design_root (e.g. design/) is a small, hand-authored \
    # .strata source subtree with no nested .git/.venv/node_modules/build/dist/target \
    # to prune -- excludes.walk_pruned would add a filter that never fires here, not \
    # change behavior, same posture sync_may_report's own WALK001 waiver documents"
    for path in sorted(design_root.rglob("*.strata")):
        text = path.read_text(encoding="utf-8")
        if "node " not in text and "store " not in text:
            continue
        result = _sync_one_file_may_extended(text, additions)
        if result is None:
            continue
        rel = path.relative_to(root).as_posix()
        results.append(
            FileMayExtendedSyncResult(
                path=rel,
                old_text=result.old_text,
                new_text=result.new_text,
                diffs=result.diffs,
            )
        )
    drifted = sum(1 for r in results if r.changed)
    _log.info(
        "sync_may_extended_report: %d file(s) scanned, %d drifted",
        len(results),
        drifted,
    )
    return Ok(SyncMayExtendedReport(files=tuple(results)))


# frob:ticket T-1545
# frob:doc docs/modules/gates.md#sys100sys104-strata-declaration-auto-fix-t-1531
# frob:tests tests/unit/strata/test_sync_may.py::TestApplySyncMayExtended.test_writes_only_changed_files  # noqa: E501
def apply_sync_may_extended(
    root: Path, report: SyncMayExtendedReport
) -> tuple[str, ...]:
    """Write every changed `FileMayExtendedSyncResult.new_text` in
    `report` back to its file, in the same load order; returns the sorted
    repo-relative paths actually rewritten. Mirrors `apply_sync_may`."""
    return _write_changed_may_files(root, report.files)


__all__ = [
    "FileMayExtendedSyncResult",
    "FileMaySyncResult",
    "MayGrantDiff",
    "SyncMayExtendedReport",
    "SyncMayReport",
    "WholeNodeMayGrantDiff",
    "apply_sync_may",
    "apply_sync_may_extended",
    "sync_may_extended_report",
    "sync_may_report",
]
