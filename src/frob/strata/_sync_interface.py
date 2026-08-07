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
promise): a node's `interface=` declaration is EXPECTED to be one
contiguous block (brace-depth matched, since `on crash { ... }`/
`on breach { ... }`/`on deploy { ... }` sub-blocks nest their own braces
inside a node body and a naive first-`}` search would truncate early), but
`_find_interface_spans` does NOT assume there is only one -- it finds
EVERY span in the body, recognizing EITHER form the grammar accepts
(module docstring's T-1198 paragraph below). T-1624: an earlier version of
this scan stopped at the first match, so a node carrying a duplicate (or
stray leftover) second `interface=` block silently kept it forever --
`_rewrite_node_interface_block` now collapses every span found into ONE,
deleting all but the merged, re-rendered block at the first span's
position -- everything else in the file, including every comment, is
copied through byte-for-byte. A node with real symbols but no existing
`interface=` declaration yet (a brand-new node, never hand-populated) gets
its block inserted directly after the node's opening `{` line, the same
"no established position, insert right after the header" convention
`sync_interface_report`'s own tests pin down.

T-1198 (`interface=` boilerplate elimination): before this ticket, SYS104's
mechanical upkeep convention was ONE bare `attr interface=X;` LINE per
symbol -- the exact mechanism this module exists to automate, but a
generator that faithfully reproduces N lines per node for a node with
hundreds of real symbols (this repo's own `tickets_gate`/`core` nodes) is
itself the boilerplate the ticket names: 4236 of `design/frob.strata`'s
5588 pre-T-1198 lines were `attr interface=X;` lines. `strata-core`'s
grammar (`parse_attrval`, `strata-core/src/parse/grammar_core.rs`) gained
a bracket-list form as pure parser sugar -- `attr interface=[Foo, Bar,
Baz];` expands, AT PARSE TIME, into the exact same `"interface=Foo"`,
`"interface=Bar"`, `"interface=Baz"` attr strings the one-line-per-symbol
form always produced, so no downstream consumer (`_elaborate.py`,
`_selfconform.py`'s SYS104 measurement, every gate that reads `Node.attrs`)
needed to change at all -- the elaborated model is byte-for-byte
identical either way. This module is the WRITER half: `_render_
interface_block` now emits that compact form, `NAMES_PER_LINE` symbol
names per wrapped line purely for readability (the grammar does not care
about the newlines inside `[...]`), instead of one line per symbol.
`_find_interface_spans` reads BOTH forms (the compact block it now
writes, and the legacy one-line-per-symbol form for backward
compatibility on a file not yet migrated) and always WRITES the compact
form -- including a one-time reformat of an already-correct legacy
declaration whose symbol SET already matches real (`single_clean` in
`_rewrite_node_interface_block`, forcing the rewrite whenever more than
one span is found OR the sole span is not already compact, even when
nothing about the SYMBOLS changed), so running `frob sys sync-interface`
once migrates an entire repo off the old form AND collapses any
already-duplicated node down to one block. Migrating this repo's own
`design/frob.strata` measured 5588 -> 2207 lines (~60% reduction),
confirmed idempotent (`frob sys sync-interface --check` reports zero
drift immediately after).

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

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import CodeBinding, bind_code
from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._errors import StrataError
from ._selfconform import _cross_node_referenced_symbols, _node_real_public_surface
from ._sysdoc import merge_models

_log = get_logger(__name__)

#: One node OR store header line, e.g. `node cli : trusted {` or
#: `store tickets_ledger : trusted {` -- captures the id so a `.strata`
#: file's raw text can be searched WITHOUT re-parsing (that would lose
#: comments); the parser/elaborator is only used to compute the
#: real/declared surface, never to regenerate this file's text. `store`
#: blocks are matched identically to `node` blocks (T-1425) because
#: `_interface_conformance_violations`/`model.nodes` already treat them as
#: first-class SYS104 subjects -- this module used to only match `node`,
#: silently skipping every store's `interface=` drift.
_NODE_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:node|store)\s+(?P<id>\S+)\b[^{]*\{\s*$"
)

#: One legacy `attr interface=<symbol>;` line -- the pre-T-1198 one-line-
#: per-symbol form `_interface_conformance_violations` still accepts (the
#: grammar never stopped supporting it) and this module still READS for
#: backward compatibility, but no longer WRITES (see
#: `_INTERFACE_BLOCK_OPEN_RE`/`_INTERFACE_BLOCK_CLOSE_RE` below).
_INTERFACE_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)attr interface=(?P<name>\S+?);\s*$"
)

#: T-1198: the compact `attr interface=[...]` block this module now WRITES
#: -- one bracket-list attr (strata-core's `parse_attrval` grammar change,
#: docs/strata/surface.md#compact-interface-attrs-t-1198) wrapped across
#: several lines purely for human readability (the parser does not care
#: about the newlines; `NAMES_PER_LINE` symbols per line, comma-separated,
#: trailing comma on every line including the last for a clean per-line
#: diff when the SET changes). Open/close are matched as separate regexes
#: since the symbol lines between them are plain comma-separated idents,
#: not individually regex-matched.
_INTERFACE_BLOCK_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)attr interface=\[\s*$")
_INTERFACE_BLOCK_CLOSE_RE = re.compile(r"^[ \t]*\];\s*$")

#: How many symbol names `_rewrite_node_interface_block` packs onto one
#: wrapped line inside a compact `interface=[...]` block -- purely a
#: readability knob, not a grammar constraint (the parser accepts any
#: whitespace/newline layout inside `[...]`).
# frob:doc docs/strata/surface.md#compact-interface-attrs-t-1198
NAMES_PER_LINE = 6


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


#: One located `interface=` declaration span: `(first_line, last_line,
#: indent, names, is_compact)` -- see `_find_interface_spans`.
_InterfaceSpan = tuple[int, int, str, list[str], bool]


def _find_interface_spans(
    lines: list[str], header_idx: int, close_idx: int
) -> list[_InterfaceSpan]:
    """Locate EVERY `interface=` declaration inside one node's body, in
    whichever form each is written (T-1198's compact `[...]` block, or the
    legacy one-line-per-symbol form, freely mixed). T-1624: this used to
    stop at the FIRST match and return it alone -- `_rewrite_node_
    interface_block` then only ever replaced that first span, silently
    leaving any SECOND (or later) block untouched. That is exactly how
    `design/frob.strata` ended up with 45 byte-identical duplicate blocks
    across ~17 nodes (T-1624): a node with an interface block anywhere but
    the very first `interface=` occurrence in its body kept accumulating a
    stale copy on every sync run that inserted at a different position (or
    on any manual edit that left an old block in place). Returning every
    span found lets the caller MERGE and dedupe them into exactly one.
    Each compact block scan skips past its own close line so a legacy
    line inside one block's symbol list (impossible today, but the regex
    alone would not rule it out) cannot be double-counted."""
    spans: list[_InterfaceSpan] = []
    idx = header_idx + 1
    while idx < close_idx:
        open_m = _INTERFACE_BLOCK_OPEN_RE.match(lines[idx])
        if open_m is not None:
            names: list[str] = []
            close_idx_inner = idx
            for j in range(idx + 1, close_idx):
                if _INTERFACE_BLOCK_CLOSE_RE.match(lines[j]):
                    close_idx_inner = j
                    break
                names.extend(
                    part.strip() for part in lines[j].split(",") if part.strip()
                )
            spans.append((idx, close_idx_inner, open_m.group("indent"), names, True))
            idx = close_idx_inner + 1
            continue
        legacy_m = _INTERFACE_LINE_RE.match(lines[idx])
        if legacy_m is not None:
            spans.append(
                (idx, idx, legacy_m.group("indent"), [legacy_m.group("name")], False)
            )
        idx += 1
    return spans


def _render_interface_block(indent: str, names: frozenset[str]) -> list[str]:
    """T-1198: render `names` as one compact `attr interface=[...]` block,
    `NAMES_PER_LINE` names per wrapped line -- the writer half of the
    boilerplate-elimination this module exists for (module docstring):
    a node with hundreds of real symbols used to cost one `attr
    interface=X;` LINE per symbol; it now costs one line per
    `NAMES_PER_LINE` symbols plus two structural lines, regardless of how
    many symbols there are."""
    sorted_names = sorted(names)
    if not sorted_names:
        return [f"{indent}attr interface=[];"]
    body_indent = indent + "    "
    lines = [f"{indent}attr interface=["]
    for start in range(0, len(sorted_names), NAMES_PER_LINE):
        chunk = sorted_names[start : start + NAMES_PER_LINE]
        lines.append(body_indent + ", ".join(chunk) + ",")
    lines.append(f"{indent}];")
    return lines


def _rewrite_node_interface_block(
    lines: list[str], header_idx: int, real: frozenset[str]
) -> tuple[list[str], NodeInterfaceDiff | None]:
    """Replace one node's `interface=` declaration(s) (`_find_interface_spans`
    -- possibly more than one span pre-T-1624) with a SINGLE compact
    `interface=[...]` block covering the sorted `real` surface (T-1198,
    `_render_interface_block`); returns the (possibly unchanged) full
    `lines` list plus the diff record, or `None` if nothing changed. T-1624:
    when more than one span is found, this ALWAYS rewrites (collapsing
    every span into one), even if the union of their declared names already
    equals `real` -- duplication itself is the defect being fixed, not just
    a symbol-set mismatch; a node that is merely duplicated, not drifted,
    must still be corrected down to one block."""
    close_idx = _node_body_span(lines, header_idx)
    spans = _find_interface_spans(lines, header_idx, close_idx)
    if not spans:
        indent = None
        declared_set: frozenset[str] = frozenset()
        single_clean = True  # nothing to migrate, nothing to dedupe
    else:
        indent = spans[0][2]
        declared_set = frozenset(name for span in spans for name in span[3])
        single_clean = len(spans) == 1 and spans[0][4]  # one span, already compact

    if declared_set == real and single_clean:
        return lines, None

    added = tuple(sorted(real - declared_set))
    removed = tuple(sorted(declared_set - real))
    header_match = _NODE_HEADER_RE.match(lines[header_idx])
    assert header_match is not None  # header_idx always matched to get here
    node_id = header_match.group("id")
    diff = NodeInterfaceDiff(node=node_id, added=added, removed=removed)

    if indent is None:
        # No existing interface= block to anchor on/copy indentation from --
        # fall back to the node body's own indent + one level (4 spaces),
        # matching this repo's existing convention throughout.
        indent = header_match.group("indent") + "    "

    new_block = _render_interface_block(indent, real)

    if spans:
        # Remove every span's line range, LAST span first, so removing a
        # later span never shifts an earlier span's already-recorded line
        # indices out from under it; the first span's own start index is
        # therefore still valid once every later span is gone, and doubles
        # as the insertion point for the single merged block.
        new_lines = list(lines)
        for first, last, _, _, _ in reversed(spans):
            del new_lines[first : last + 1]
        insert_at = spans[0][0]
        new_lines[insert_at:insert_at] = new_block
    else:
        # Nothing declared yet: insert right after the node's opening line.
        new_lines = lines[: header_idx + 1] + new_block + lines[header_idx + 1 :]
    return new_lines, diff


def _sync_one_file(
    text: str,
    binding: CodeBinding,
    root: Path,
    cross_referenced: dict[str, frozenset[str]],
) -> FileSyncResult | None:
    """Compute (and apply, in-memory) every node drift in one `.strata`
    file's raw `text`; returns `None` if the file declares no node headers
    at all (nothing for this command to do). `cross_referenced` (T-1625,
    `_selfconform._cross_node_referenced_symbols`, computed ONCE per
    report and threaded through rather than recomputed per file/node) is
    the same required-surface narrowing SYS104 itself now enforces -- this
    writer and that gate MUST agree on what "required" means, or every
    sync run would immediately re-drift against the gate it is meant to
    satisfy."""
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
        required = real & cross_referenced.get(node_id, frozenset())
        declared = frozenset(_node_attr_values_at(lines, idx))
        if not declared and not required:
            continue
        before_len = len(lines)
        lines, diff = _rewrite_node_interface_block(lines, idx, required)
        if diff is not None:
            diffs.append(diff)
            offset += len(lines) - before_len
    new_text = "\n".join(lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return FileSyncResult(path="", old_text=text, new_text=new_text, diffs=tuple(diffs))


def _node_attr_values_at(lines: list[str], header_idx: int) -> list[str]:
    """The declared `interface=` symbol names inside the node body opened at
    `lines[header_idx]`, across EVERY span found (`_find_interface_spans`)
    -- used only for the early-continue "nothing declared, nothing real"
    skip; the authoritative diff computation still happens inside
    `_rewrite_node_interface_block`."""
    close_idx = _node_body_span(lines, header_idx)
    spans = _find_interface_spans(lines, header_idx, close_idx)
    return [name for span in spans for name in span[3]]


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
    # T-1625: computed ONCE for the whole report, not per file/node -- see
    # `_sync_one_file`'s docstring for why this must be the SAME view
    # SYS104 itself uses.
    cross_referenced = _cross_node_referenced_symbols(binding, root)

    design_root = root / design_dir
    results: list[FileSyncResult] = []
    # frob:waive WALK001 reason="design_root (e.g. design/) is a small, hand-authored \
    # .strata source subtree with no nested .git/.venv/node_modules/ build/dist/target \
    # to prune -- excludes.walk_pruned would add a filter that never fires here, not \
    # change behavior"
    for path in sorted(design_root.rglob("*.strata")):
        text = path.read_text(encoding="utf-8")
        # T-1425: this used to check `"node " not in text` only, silently
        # skipping a store-only design file (no `node ` substring anywhere)
        # before `_sync_one_file` ever ran -- `_NODE_HEADER_RE` itself uses
        # `^`/`$` without MULTILINE, so `.search(text)` on the whole file
        # only ever matches a header on the FIRST line, making this
        # substring fallback the check that actually mattered in practice.
        if "node " not in text and "store " not in text:
            continue
        result = _sync_one_file(text, binding, root, cross_referenced)
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
