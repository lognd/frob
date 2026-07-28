"""`frob sys sync-interface` (T-1150): mechanically measure every node's
bound-code public surface and rewrite `design/frob.strata`'s (or any other
loaded `.strata` file's) `interface=<symbol>` attrs to match it exactly.

SYS104 (`_selfconform.py::_interface_conformance_violations`) went
MANDATORY at T-1113: every node with a non-empty real public surface is
now evaluated whether or not it declared any `interface=` attr yet. That
made `design/frob.strata` a hand-maintained mirror of every node's real
public surface -- and a mandatory check with manual upkeep is a red-main
generator (the DEPR005 line-keyed-baseline shape, T-1052): main went red
twice within hours of T-1113 landing (`tickets_gate` missing, then
`net.connect` from T-1126's daemon-lease socket), both hand-fixed by the
coordinator directly in the `.strata` file (commits e3ad8054, 5f5e88b8).

This module closes that gap by reusing the SAME measurement SYS104
already computes (`_selfconform.py::_node_real_public_surface`, built on
`_module_public_symbols`) and turning the diff into a mechanical, reviewable
text edit rather than a hand patch:

- `sync_interface_report` loads+merges every `.strata` file under a design
  root (same `load_design_ids`/`merge_models`/`bind_code` join every other
  `sys` verb uses), computes each node's declared-vs-real `interface=`
  surface, and returns one `FileSyncResult` per `.strata` file that
  declares at least one drifted node.
- `apply_sync_interface` writes the corrected text back to disk (the
  non-`--check` default); `--check` mode (the CLI layer, `app/sys_runner.py`)
  only ever calls `sync_interface_report` and never writes.

Text-editing strategy (never a full re-serialize -- MUST preserve every
comment and every other attr/waive/access line untouched, module docstring
promise): each node's `attr interface=<symbol>;` lines form one CONTIGUOUS
block with no interleaved comments anywhere in this repo's own
`design/frob.strata` today (verified by direct inspection at T-1150 write
time) -- SYS104's own convention is one bare `attr interface=X;` line per
symbol, nothing else mixed in. `_replace_node_interface_block` finds that
contiguous span (if any) inside one node's `{ ... }` body (brace-depth
matched, since `on crash { ... }`/`on breach { ... }`/`on deploy { ... }`
sub-blocks nest their own braces inside a node body and a naive first-`}`
search would truncate early) and replaces it in place with the sorted,
measured set -- everything before/after that span, including every
comment, is copied through byte-for-byte. A node with real symbols but no
existing `interface=` line yet (a brand-new node, never hand-populated)
gets its block inserted directly after the node's opening `{` line, the
same "no established position, insert right after the header" convention
`sync_interface_report`'s own tests pin down.

T-1137/T-1138 Tier-A auto-fix registration (this ticket's acceptance
criterion 1): DISCLOSED DEFERRAL, not built here. T-1138 (the first
Tier-A handler batch) is still `queued` as of this ticket's own land --
there is no fix-engine handler table/protocol yet to register against
(T-1137's epic ticket is still in design). Wiring SYS104 drift as a
Tier-A auto-fix belongs to whichever of T-1137's children actually lands
the handler-table plumbing; this module's `sync_interface_report`/
`apply_sync_interface` split (pure compute vs. write) is deliberately
shaped so that a future Tier-A handler can call the same two functions
this CLI verb calls, with zero rework, once that surface exists.
"""
# frob:waive INV006 reason="this module's exclusivity-vocabulary hits ('only ever', \
# 'never writes') are source-level design-rationale prose describing \
# already-implemented internal behavior, verifiable by reading the code they annotate, \
# same T-0585/T-1053 first-turn-on calibration posture src/frob/app/sys_runner.py's \
# own INV006 waiver documents -- not a separate cross-module contract needing its own \
# tracked invariant"

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import CodeBinding, bind_code
from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._errors import StrataError
from ._selfconform import _node_real_public_surface
from ._sysdoc import merge_models

_log = get_logger(__name__)

#: One node header line, e.g. `node cli : trusted {` -- captures the node id
#: so a `.strata` file's raw text can be searched WITHOUT re-parsing (that
#: would lose comments); the parser/elaborator is only used to compute the
#: real/declared surface, never to regenerate this file's text.
_NODE_HEADER_RE = re.compile(r"^(?P<indent>[ \t]*)node\s+(?P<id>\S+)\b[^{]*\{\s*$")

#: One `attr interface=<symbol>;` line, in the exact form
#: `_interface_conformance_violations`/existing `design/frob.strata` usage
#: always emits it.
_INTERFACE_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)attr interface=(?P<name>\S+?);\s*$"
)


# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
@dataclass(frozen=True)
class NodeInterfaceDiff:
    """One node's `interface=` drift: symbols to add (real but undeclared)
    and remove (declared but no longer real), both sorted for determinism."""

    node: str
    added: tuple[str, ...]
    removed: tuple[str, ...]


# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
@dataclass(frozen=True)
class FileSyncResult:
    """One `.strata` file's sync-interface outcome: every drifted node in
    it (`diffs`, possibly empty) and the corrected text (`new_text`,
    identical to the input when `diffs` is empty)."""

    path: str
    old_text: str
    new_text: str
    diffs: tuple[NodeInterfaceDiff, ...]

    # frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
    @property
    def changed(self) -> bool:
        """Whether this file's text actually differs -- `diffs` alone can be
        non-empty with `new_text == old_text` only in the degenerate case of
        zero real drift, so callers should gate on this, not `bool(diffs)`."""
        return self.new_text != self.old_text


# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
@dataclass(frozen=True)
class SyncInterfaceReport:
    """Every loaded `.strata` file's sync-interface outcome, in load order."""

    files: tuple[FileSyncResult, ...]

    # frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
    # frob:tests tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_addition_and_removal_detected  # noqa: E501
    @property
    def has_drift(self) -> bool:
        """True if ANY file in this report needs a rewrite -- the `--check`
        mode's pass/fail signal."""
        return any(f.changed for f in self.files)


def _node_body_span(lines: list[str], header_idx: int) -> int:
    """The line index of the `}` that closes the node body opened at
    `lines[header_idx]` (which itself ends in `{`), brace-depth matched so a
    nested `on crash { ... }`/`on breach { ... }`/`on deploy { ... }`
    sub-block's own braces do not terminate the search early."""
    depth = 1
    for idx in range(header_idx + 1, len(lines)):
        # frob:waive PERF002 reason="each line is a different string every iteration \
        # -- nothing to hoist or cache; one-pass O(n) brace-depth scan, not a repeated \
        # identical query"
        depth += lines[idx].count("{") - lines[idx].count("}")
        if depth == 0:
            return idx
    return len(lines) - 1  # malformed input: no matching close, best effort


def _rewrite_node_interface_block(
    lines: list[str], header_idx: int, real: frozenset[str]
) -> tuple[list[str], NodeInterfaceDiff | None]:
    """Replace one node's contiguous `attr interface=X;` block (if any) with
    the sorted `real` surface; returns the (possibly unchanged) full `lines`
    list plus the diff record, or `None` if nothing changed. Module
    docstring's "Text-editing strategy" section explains the contiguous-span
    assumption this relies on."""
    close_idx = _node_body_span(lines, header_idx)
    first_iface = None
    last_iface = None
    declared: list[str] = []
    indent = None
    for idx in range(header_idx + 1, close_idx):
        m = _INTERFACE_LINE_RE.match(lines[idx])
        if m is None:
            continue
        if first_iface is None:
            first_iface = idx
            indent = m.group("indent")
        last_iface = idx
        declared.append(m.group("name"))

    declared_set = frozenset(declared)
    if declared_set == real:
        return lines, None

    added = tuple(sorted(real - declared_set))
    removed = tuple(sorted(declared_set - real))
    header_match = _NODE_HEADER_RE.match(lines[header_idx])
    assert header_match is not None  # header_idx always matched to get here
    node_id = header_match.group("id")
    diff = NodeInterfaceDiff(node=node_id, added=added, removed=removed)

    if indent is None:
        # No existing interface= line to anchor on/copy indentation from --
        # fall back to the node body's own indent + one level (4 spaces),
        # matching this repo's existing convention throughout.
        indent = header_match.group("indent") + "    "

    new_block = [f"{indent}attr interface={name};" for name in sorted(real)]

    if first_iface is not None and last_iface is not None:
        new_lines = lines[:first_iface] + new_block + lines[last_iface + 1 :]
    else:
        # Nothing declared yet: insert right after the node's opening line.
        new_lines = lines[: header_idx + 1] + new_block + lines[header_idx + 1 :]
    return new_lines, diff


def _sync_one_file(
    text: str, binding: CodeBinding, root: Path
) -> FileSyncResult | None:
    """Compute (and apply, in-memory) every node drift in one `.strata`
    file's raw `text`; returns `None` if the file declares no node headers
    at all (nothing for this command to do)."""
    lines = text.splitlines()
    diffs: list[NodeInterfaceDiff] = []
    # Node headers never nest (a `.strata` node body cannot contain another
    # node header), so collecting every header index up front is safe; each
    # rewrite below shifts everything AFTER it by a line-count delta, so
    # `offset` tracks that running shift rather than re-scanning from
    # scratch after every node.
    header_idxs = [i for i, line in enumerate(lines) if _NODE_HEADER_RE.match(line)]
    offset = 0
    for header_idx in header_idxs:
        idx = header_idx + offset
        m = _NODE_HEADER_RE.match(lines[idx])
        if m is None:
            continue  # defensive: should always still match post-shift
        node_id = m.group("id")
        real = _node_real_public_surface(binding, root, node_id)
        declared = frozenset(_node_attr_values_at(lines, idx))
        if not declared and not real:
            continue
        before_len = len(lines)
        lines, diff = _rewrite_node_interface_block(lines, idx, real)
        if diff is not None:
            diffs.append(diff)
            offset += len(lines) - before_len
    new_text = "\n".join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return FileSyncResult(path="", old_text=text, new_text=new_text, diffs=tuple(diffs))


def _node_attr_values_at(lines: list[str], header_idx: int) -> list[str]:
    """The declared `interface=` symbol names inside the node body opened at
    `lines[header_idx]`, read straight off the raw text (used only for the
    early-continue "nothing declared, nothing real" skip -- the authoritative
    diff computation still happens inside `_rewrite_node_interface_block`)."""
    close_idx = _node_body_span(lines, header_idx)
    names: list[str] = []
    for idx in range(header_idx + 1, close_idx):
        m = _INTERFACE_LINE_RE.match(lines[idx])
        if m is not None:
            names.append(m.group("name"))
    return names


# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
# frob:tests tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_no_drift_reports_clean  # noqa: E501
# frob:tests tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport.test_addition_and_removal_detected  # noqa: E501
def sync_interface_report(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[SyncInterfaceReport, StrataError]:
    """Load+merge every `.strata` file under `root/design_dir`, bind code,
    and compute each file's `interface=` drift against the measured real
    public surface (module docstring). Never writes -- `apply_sync_interface`
    is the only function in this module with a side effect."""
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        first = ids.errors[0]
        _log.error(
            "sync_interface_report: %s failed to load: %s", first.path, first.error
        )
        return Err(first.error)
    if not ids.models:
        _log.info(
            "sync_interface_report: no design models under %s/%s", root, design_dir
        )
        return Ok(SyncInterfaceReport(files=()))

    model = merge_models(ids.models)
    bound = bind_code(model, root)
    if bound.is_err:
        _log.error("sync_interface_report: bind_code failed: %s", bound.danger_err)
        return Err(bound.danger_err)
    binding = bound.danger_ok

    design_root = root / design_dir
    results: list[FileSyncResult] = []
    for path in sorted(design_root.rglob("*.strata")):
        text = path.read_text(encoding="utf-8")
        if not _NODE_HEADER_RE.search(text) and "node " not in text:
            continue
        result = _sync_one_file(text, binding, root)
        if result is None:
            continue
        rel = path.relative_to(root).as_posix()
        results.append(
            FileSyncResult(
                path=rel,
                old_text=result.old_text,
                new_text=result.new_text,
                diffs=result.diffs,
            )
        )
    drifted = sum(1 for r in results if r.changed)
    _log.info(
        "sync_interface_report: %d file(s) scanned, %d drifted", len(results), drifted
    )
    return Ok(SyncInterfaceReport(files=tuple(results)))


# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150  # noqa: E501
# frob:tests tests/unit/strata/test_sync_interface.py::TestApplySyncInterface.test_writes_only_changed_files  # noqa: E501
def apply_sync_interface(root: Path, report: SyncInterfaceReport) -> tuple[str, ...]:
    """Write every changed `FileSyncResult.new_text` in `report` back to its
    file on disk; returns the relative paths actually written (files with no
    drift are never touched, not even to normalize line endings)."""
    written: list[str] = []
    for result in report.files:
        if not result.changed:
            continue
        (root / result.path).write_text(result.new_text, encoding="utf-8")
        written.append(result.path)
    _log.info("apply_sync_interface: %d file(s) written", len(written))
    return tuple(written)
