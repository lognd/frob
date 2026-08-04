# frob:waive SCOPE001 reason="T-1402: this file needed only a mechanical, necessary \
# rename of a stale frob:waive EXHAUST001 comment to EXHAUST003 (the EXHAUST001 \
# precision fix, declared scope src/frob/gates/_exhaustive_handling.py) or (this file, \
# _tickets_gate.py, _waive.py) is the actual TICK011 fix itself -- frob ticket scope \
# --add refuses it: T-1279 (TEST005 burn-down) holds a concurrent in-progress lease on \
# src/frob/gates/** for the whole package, so this ticket cannot formally register the \
# file in its own declared scope until T-1279 closes or narrows; see this ticket's \
# Done report for the full disclosure"
"""frob.gates -- enforcement gates, policy, and invariants (docs/modules/gates.md).

The drift half (nothing declared is silently broken) and the coverage half
(nothing new escapes declaration) meet here. Per docs/rework.md's cycle-
avoidance rule, `frob.gates` is the ONLY module that joins graph edge
targets against `frob.tickets`, `invariants/`, and `frob.policy` state --
`frob.graph` treats every edge target as an opaque string.

Gates are pure functions over already-loaded state (`GraphSnapshot`,
`TicketQueue`, `LockFile`, `Diff`, `CollectedTests`, invariants, policy
rules, coverage). `run_gates` is the only function in this package that
performs IO; it loads everything once and runs the gates in parallel via
`ThreadPoolExecutor`, mirroring `frob.check`'s existing parallel-tools
posture. The public gate functions stay defined in this module so their
`frob:doc`/`frob:tests` bindings keep their `__init__.py` symref; each rule
is decomposed into small private helpers alongside it.
"""

from __future__ import annotations

import ast
import fnmatch
import functools
import hashlib
import logging
import multiprocessing
import os
import re
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from frob.graph.callgraph import CallGraph

from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

from frob.excludes import is_test_file
from frob.gates._arch import arch_gate
from frob.gates._baseline import (
    delta_violations,
    is_baseline_stale,
    load_baseline,
    stamp_baseline,
    violation_fingerprint,
)
from frob.gates._coverage import (
    coverage_lock_diff,
    load_coverage,
    load_coverage_lock,
    load_stamp,
    stamp_coverage,
    write_coverage_lock,
)
from frob.gates._coverage import (
    exclude_filtered_coverage as _coverage_exclude_filtered_coverage,
)
from frob.gates._cve_fingerprint_scan import cve_fingerprint_scan_gate
from frob.gates._dead_symbols import dead_symbol_gate
from frob.gates._debt_deprecated import (
    _release_expired_deprecated_violations,
    _release_open_debt_violations,
    debt_gate,
    deprecated_current_references,
    deprecated_gate,
    list_debt,
    list_deprecated,
)
from frob.gates._decisions_compliance import compliance_gate, decisions_gate
from frob.gates._design_invariants import inv007_violations, inv008_violations
from frob.gates._docblocks import doc004_gate, doc005_gate
from frob.gates._docenum import docenum001_gate
from frob.gates._doclink_docanchor import (
    _docanchor_check_edge,
    docanchor_gate,
    doclink_gate,
    docmake_gate,
    docstatus_gate,
)
from frob.gates._docptr import doc006_gate
from frob.gates._dup import dup_gate
from frob.gates._exclude_hazard import exclude_hazard_gate
from frob.gates._exhaustive_handling import exhaustive_handling_gate
from frob.gates._ffi_boundary import ffi_boundary_gate
from frob.gates._filehash import _SOURCE_EXTS
from frob.gates._fix_engine import (  # noqa: F401 -- T-1138's public --fix API surface, consumed by a later CLI-wiring batch (T-1137 epic) and tests/test_gates.py directly
    FixApplied,
    apply_tier_a_fixes,
    fix_doc002_unique_slug,
    fix_doc007_dotted_form,
    fix_tick002_renumber,
)
from frob.gates._fmt_directives import (
    FmtChange,
    FmtReport,
    format_paths,
)
from frob.gates._fuzz import fuzz_gate
from frob.gates._gate_cache import evaluate_cacheable_gate, model_side_channel_key
from frob.gates._gate_cache import invalidate as invalidate_gate_cache
from frob.gates._inv import (  # noqa: F401 -- INV006_SRC_DIRS/INV006_SRC_SUFFIXES
    # re-exported as _fix_engine.py's direct `from frob.gates import ...` surface
    INV006_SRC_DIRS,
    INV006_SRC_SUFFIXES,
    inv003_gate,
    inv004_gate,
    inv006_gate,
    invariant_gate,
)
from frob.gates._lang_conformance import (
    lang_conformance_gate,
    project_lang_conformance_gate,
)
from frob.gates._models import (
    CoverageData,
    CoverageError,
    DebtEntry,
    DeprecatedEntry,
    GateConfig,
    GateError,
    GateReport,
    GateStats,
    PreworkSweep,
    Severity,
    SystemSpec,
    TestPolicy,
    Violation,
    WaiverRef,
)
from frob.gates._mutation_evidence import (
    bug_repro_violations,
    mutation_evidence_violations,
)
from frob.gates._negexist import negexist001_gate
from frob.gates._opaque import opaque_gate
from frob.gates._parse_failures import parse_failure_gate
from frob.gates._pii_structural import pii_structural_gate
from frob.gates._prework import load_prework, record_prework, sweep_ticket
from frob.gates._protocol_summary import protocol_summary_gate
from frob.gates._ratchet import (
    RatchetEntry,
    RatchetError,
    RatchetPool,
    clear_ratchet_entry,
    snapshot_ratchet,
)
from frob.gates._refs import ref_gate
from frob.gates._registry_exhaustiveness import registry_gate
from frob.gates._render_lint import render_lint_gate
from frob.gates._secrets import fake_marker_staleness_gate, secrets_gate
from frob.gates._suppress import (
    SuppressionDialect,
    suppress001_gate,
    suppression_dialects,
)
from frob.gates._sys import (  # noqa: F401 -- _DEFAULT_DESIGN_DIR/_claims_markers/_design_dir re-exported as tests/test_gates.py's + _waive_comments.py's monkeypatch/direct-call surface
    _DEFAULT_DESIGN_DIR,
    _claims_markers,
    _design_dir,
    _load_test_config,
    sys_gate,
)
from frob.gates._taint_gate import taint_gate
from frob.gates._tickets_gate import (  # noqa: F401 -- _tick004_queue_rot re-exported for tests/test_tickets_priority.py's direct import
    _tick004_queue_rot,
    tickets_gate,
)
from frob.gates._todo_fmt import _todo001, _todo003_long_deferred, fmt_gate
from frob.gates._waive import (
    _KNOWN_GATE_RULES,
    _UNWAIVABLE_RULES,
    SCOPED_RUN_FLAKY_RULE_IDS,
    _apply_severity_overrides,
    _apply_waivers,
    _dsl001_violations,
    _match_waiver,
    _waive001_violations,
    _waive002_violations,
    _waive003_violations,
    _waive004_violations,
    _waive005_violations,
    known_gate_rule_ids,
)
from frob.gates._waive_comments import (
    _place001,
    _waive006_binding_ticket_refs,
    _waive006_comment_violations,
    _waive006_strata_violations,
    _waive007_comment_violations,
    _waive007_is_exempt_dangling_ref,
    _waive007_strata_violations,
    waive006_gate,
    waive007_gate,
)
from frob.gates._waive_lease import active_ticket, ticket_lease_pin
from frob.gates._walk_lint import walk_lint_gate
from frob.gates._wire import wire_gate
from frob.gates.decisions import DecisionError
from frob.gates.invariants import Invariant, InvariantError, load_invariants
from frob.gitio import Diff, Hunk, run_argv, working_diff
from frob.gitio import repo_root as _git_repo_root
from frob.graph import (
    Edge,
    EdgeKind,
    GraphSnapshot,
    build_graph,
    edges_from,
)
from frob.graph._generated import is_generated_source
from frob.graph._models import LockFile, SymbolRecord
from frob.graph.affects import affects as _graph_affects
from frob.graph.lock import drift as _graph_drift
from frob.graph.lock import load_lock
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile, RawSymbol
from frob.lang._walk_rust import _MACRO_SYMBOL_SUFFIX
from frob.logging import get_logger

# Import from frob.testing's submodules directly, not the frob.testing
# package __init__ -- that __init__ imports frob.gates (via
# frob.testing._coverage_wait -> frob.gates._coverage), so importing the
# *package* here would form a circular import that only survived by
# accident of import order (T-0634: standalone `import frob.testing`
# broke). Neither frob.testing._collect nor frob.testing._models imports
# frob.gates, so this is cycle-free.
from frob.testing._collect import (
    collect_cpp_tests,
    collect_python_tests,
    collect_rust_tests,
    collect_ts_tests,
    python_collection_failure_detail,
)
from frob.testing._models import CollectedTests
from frob.tickets import Ticket, TicketQueue, TicketState, load_queue
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    _scope_globs,
    _split_scope_entries,
    is_cmd_evidence,
    matches_collected,
    scope_matches,
)
from frob.tickets._provisional import (  # noqa: F401 -- re-exported so tests/test_tickets_collision.py's monkeypatch("frob.gates.on_default_branch", ...) still resolves
    on_default_branch,
)
from frob.tickets._store import _parse_ledger as _tickets_parse_ledger

_log = get_logger(__name__)

_OPEN_STATES = frozenset(
    s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
)


# ---------------------------------------------------------------------------
# Hunk-to-symref resolution
# ---------------------------------------------------------------------------
# frob.testing._select.select_tests does the same span-overlap match inline as
# part of a larger selection algorithm and does not expose it as a standalone
# helper, so it is not importable in isolated form; the overlap primitive is
# reimplemented here (documented duplicate, same posture as the extension-
# table duplicates already accepted across frob.graph/frob.testing/frob.policy).


def _overlaps(hunk_span: tuple[int, int], sym_span: tuple[int, int]) -> bool:
    """True if two inclusive 1-indexed line ranges intersect."""
    return hunk_span[0] <= sym_span[1] and sym_span[0] <= hunk_span[1]


def _touched_symrefs(diff: Diff, snapshot: GraphSnapshot) -> set[str]:
    """Every symbol whose span overlaps a diff hunk in the same file."""
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    touched: set[str] = set()
    for record in snapshot.symbols.values():
        for span in hunks_by_file.get(record.id.path, ()):
            if _overlaps(span, record.span):
                touched.add(record.symref)
                break
    return touched


def _touched_files(diff: Diff) -> set[str]:
    """Every file path touched anywhere in `diff`."""
    return {hunk.file for hunk in diff.hunks}


def _symref_to_nodeid(symref: str) -> str:
    """`path::a.b` -> `path::a::b`, the pytest node id spelling of a qualname.

    frob:ticket T-0324
    A parametrized test's `frob:tests`/evidence symref carries its case
    suffix verbatim (`path::a.b[015-python-3.11.4]`) -- pytest node ids for
    a `@pytest.mark.parametrize`-expanded case routinely contain their own
    literal dots (version strings, floats, dotted module paths passed as
    case values). A blanket `qualname.replace('.', '::')` over the WHOLE
    qualname corrupted those in-bracket dots too (`3.11.4` ->`3::11::4`),
    so a bracketed case id could never resolve against its real collected
    node id even though the bracket-less base did (only the base's dots,
    if any, sit outside a `[...]` suffix). Only the qualname portion before
    the first `[` is a dotted Class.method path; the `[...]` suffix (if
    any) is opaque pytest-generated case text and must pass through
    unchanged."""
    path, _, qualname = symref.partition("::")
    head, bracket, tail = qualname.partition("[")
    return f"{path}::{head.replace('.', '::')}{bracket}{tail}"


# frob:ticket T-0949
@functools.lru_cache(maxsize=8)
def _case_ids_by_base(node_ids: frozenset[str]) -> dict[str, tuple[str, ...]]:
    """Every collected `base[case-id]` node id grouped by its pre-bracket
    `base`, computed ONCE per distinct `node_ids` value and memoized
    (T-0949 root cause, second dominator): `_node_id_collected` and
    `_case_count` each used to independently re-scan the FULL `node_ids`
    set (thousands of ids) with a linear `startswith()` loop, once per
    edge/symbol looked up -- `test_gate`'s own isolated-call cProfile
    showed this exact shape (`str.startswith`, ~50M calls) as the single
    largest remaining cost after the sibling `_leaf_snake_index` fix. This
    precomputes the base->cases grouping once so both callers do an O(1)
    dict lookup instead. `node_ids` (a `frozenset`) is a valid `lru_cache`
    key on its own; unlike `_leaf_snake_index` this needs no wrapping
    `CollectedTests` model."""
    index: dict[str, list[str]] = {}
    for node_id in node_ids:
        base, bracket, _ = node_id.partition("[")
        if bracket:
            index.setdefault(base, []).append(node_id)
    return {base: tuple(cases) for base, cases in index.items()}


# frob:ticket T-0275
def _node_id_collected(base_node_id: str, node_ids: frozenset[str]) -> bool:
    """True if `base_node_id` was collected, either verbatim or as a
    `@pytest.mark.parametrize`-expanded id.

    `pytest --collect-only` never emits the bare `path::func` id for a
    parametrized test -- every collected id carries a `[case-id]` suffix
    (e.g. `path::func[water-293.15-...]`), one per parametrize case, and
    the bare id is never itself a member of the collected set. A
    `frob:tests` directive's src resolves to the bare id regardless of
    whether the bound function happens to be parametrized (the comment
    DSL has no reason to know or care), so an exact-membership check
    alone can never validate a directive bound to a parametrized test --
    the same directive placed above a plain, undecorated `def` validates
    fine, which is what made this look like a decorator-attachment bug
    (feldspar FROBLEMS.md 2026-07-18, `test_library_thermo.py`) until
    traced to the actual mismatch: parametrize-suffix expansion, not
    comment-to-symbol binding (`frob.lang._extract` already resolves the
    binding correctly in both cases -- proven directly, not assumed).

    T-0949: the prefix half of this check now consults `_case_ids_by_base`'s
    memoized grouping instead of scanning `node_ids` itself."""
    if base_node_id in node_ids:
        return True
    return base_node_id in _case_ids_by_base(node_ids)


# frob:ticket T-0318
def _macro_symbol_file(src: str) -> str | None:
    """The file path `src` names, if `src` is a T-0318 test-macro stand-in
    symbol (`_walk_rust.py::_macro_symbol` mints a qualname whose leaf
    segment ends with `_MACRO_SYMBOL_SUFFIX`, e.g. `path::tests.proptest!`)
    -- else None.

    A `frob:tests` directive placed above a `proptest! { ... }` block binds
    to this stand-in (real AST node, real span) rather than falling through
    to the bare-file-path fallback, but the stand-in still cannot be matched
    node-id-exact against `cargo test --list` output: proptest's expansion
    synthesizes one real `#[test]` fn per case at compile time, each under
    its OWN name (`fn test_foo(...)` inside the macro's token tree), never
    under a `proptest!`-named node id. `_node_id_collected`'s exact/prefix
    match can therefore never see them. The only association frob CAN prove
    without parsing the macro's opaque token tree for `fn` names (a much
    larger, separately-scoped effort) is coarser: "this file's macro block
    is satisfied if the file has at least one collected case at all" --
    file-granularity, not case-exact. Callers use this to switch from
    node-id matching to a same-file collected-id check."""
    path, sep, qualname = src.partition("::")
    if not sep or not qualname:
        return None
    leaf = qualname.rsplit(".", 1)[-1]
    return path if leaf.endswith(_MACRO_SYMBOL_SUFFIX) else None


def _macro_file_collected(file_path: str, node_ids: frozenset[str]) -> bool:
    """True if any cargo-collected node id belongs to `file_path` (T-0318
    file-granularity satisfaction for a test-macro stand-in symbol)."""
    prefix = f"{file_path}::"
    return any(node_id.startswith(prefix) for node_id in node_ids)


def _site_from_edge_origin(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin string."""
    file_part, sep, line_part = origin.rpartition(":")
    if sep and line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


# frob:ticket T-1114
def _edges_of_kind(snapshot: GraphSnapshot, kind: EdgeKind) -> tuple[Edge, ...]:
    """All edges of one `EdgeKind` in `snapshot` -- the shared shape behind
    `_debt_edges`/`_deprecated_edges` (`frob.gates._debt_deprecated`),
    `_establishes_claims` (`frob.gates._design_invariants`), and
    `_waive_edges` (`frob.gates._waive`), consolidated here (T-1114's
    abstraction-opportunity triage) rather than left as four independently
    maintained one-liners with the identical body. Lives alongside
    `_site_from_edge_origin`/`_OPEN_STATES` -- this module's established
    home for a helper shared back into split-out gate submodules via a
    call-time import, avoiding the init-time circular import a top-level
    import from those submodules into `__init__.py` would otherwise
    require."""
    return tuple(e for e in snapshot.edges if e.kind == kind)


def _is_test_path(path: str) -> bool:
    """Test code is not public API; doc obligations do not apply to it."""
    parts = PurePosixPath(path).parts
    name = PurePosixPath(path).name
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


def _interface_package(path: str) -> str:
    """The interface unit a file belongs to: `src/<pkg>/<subpkg>` (or shorter)."""
    parts = PurePosixPath(path).parts
    return (
        str(PurePosixPath(*parts[:3]))
        if len(parts) >= 3
        else str(PurePosixPath(path).parent)
    )


def _glob_prefix_match(path: str, glob: str) -> bool:
    """True if `path` sits under a `[[system]].paths` glob's directory prefix."""

    return fnmatch.fnmatch(path, glob) or path.startswith(glob.split("*")[0])


def _snake(name: str) -> str:
    """`CamelCase`/`getHTTP` -> `camel_case`/`get_http` for convention matching."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# frob:ticket T-0949
@functools.lru_cache(maxsize=8)
def _leaf_snake_index(tests: CollectedTests) -> tuple[tuple[str, str], ...]:
    """`(node_id, snake_cased_leaf)` for every node id in `tests`, computed
    ONCE per distinct `CollectedTests` value and memoized (T-0949 root
    cause): `_inferred_unit_cases`/`_test015_record_violation` each used to
    call `_snake()` on every collected node id's leaf FROM SCRATCH for
    every public symbol they were asked about -- an O(symbols x node_ids)
    re-`_snake()` cost that `test_gate`'s own isolated-call cProfile
    (T-0949) showed dominating its wall time (`_snake`/`re.sub` alone: over
    30s of a ~106s isolated run). Hoisting the per-node-id `_snake()` call
    to run once here, keyed on `tests` (a frozen, hashable pydantic model,
    so a valid `lru_cache` key), turns the remaining per-symbol work into a
    plain regex `.search()` over an already-computed leaf string instead of
    recomputing that string on every call."""
    return tuple(
        (node_id, _snake(node_id.rsplit("::", 1)[-1])) for node_id in tests.node_ids
    )


# frob:ticket T-0298
def _is_path_level_evidence(evidence: str) -> bool:
    """True if `evidence` names a file or directory rather than a single
    test node (`path::qualname`) -- no `::` at all, e.g. `tests/test_vet.py`
    or `tests/unit/deploy`."""
    return "::" not in evidence


# frob:ticket T-0298
# frob:invariant INV-013
# invariant spec: [INV-013](invariants/INV-013.md)
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov003_rejects_empty_directory_level_evidence  # noqa: E501
def _path_level_evidence_collected(evidence: str, tests: CollectedTests) -> bool:
    """COV003 file-/directory-level evidence resolution: `evidence` (a bare
    path with no `::`) resolves iff at least one collected node id lives
    under it -- either AS that exact file (`evidence::...`) or inside that
    directory (`evidence/...`).

    T-0298: a refactor touching ~20 files naturally produces evidence at
    file granularity ("this whole test file passes"), not one node id per
    file; forcing node-level ids for that shape of change is what led two
    real agents (root-cause incident, 2026-07-19 main-red) to record
    unresolvable ids like `tests/test_vet.py` or `tests/unit/deploy` that
    COV003 could never validate. This is deliberately NOT vacuous: an empty
    or nonexistent path (zero matching collected node ids) still fails --
    "this file/dir passes" only counts when something under it actually
    collected. Node-level evidence (`_evidence_collected`) remains the
    preferred, more precise granularity and is tried first by
    `_evidence_valid_for_ticket`; this is the coarser fallback, not a
    replacement."""
    stripped = evidence.rstrip("/")
    file_prefix = f"{stripped}::"
    dir_prefix = f"{stripped}/"
    return any(
        node.startswith(file_prefix) or node.startswith(dir_prefix)
        for node in tests.node_ids
    )


def _evidence_collected(evidence: str, tests: CollectedTests) -> bool:
    """Exact node-id membership, or bare-function match for parametrized
    tests (`f` satisfies evidence when only `f[param]` variants collect) --
    via `frob.tickets._models.matches_collected`, the single shared
    implementation (D-11 dedupe; `frob.tickets.add_evidence` used to carry
    an independent, hand-written copy of this exact rule). Node-level
    resolution is tried first (preferred, most precise); a bare file- or
    directory-path evidence id (T-0298, no `::`) falls back to
    `_path_level_evidence_collected` -- "any collected node under this
    path" -- rather than failing outright."""
    if matches_collected(evidence, tests.node_ids):
        return True
    if _is_path_level_evidence(evidence):
        return _path_level_evidence_collected(evidence, tests)
    return False


# frob:ticket T-0215
def _evidence_valid_for_ticket(
    evidence: str, ticket: Ticket, tests: CollectedTests
) -> bool:
    """Whether `evidence` counts as proof `ticket` is actually done: a
    collected pytest node id (`_evidence_collected`), OR -- for a
    docs-kind ticket ONLY -- a well-formed `cmd:<command> exit=0
    sha256=<12-hex>` entry (T-0215's non-pytest evidence channel, review
    round 2). `frob check` cannot cheaply re-run an arbitrary recorded
    command on every invocation (the command may be slow, non-idempotent,
    or depend on state that has since moved on) -- the cmd: digest is
    record-time attestation, not something COV003 re-verifies. What COV003
    CAN and does check cheaply: shape (`is_cmd_evidence`, mirrors the exact
    regex `run_cmd_evidence` writes) AND kind (`ticket.kind` must be in
    `CMD_EVIDENCE_ALLOWED_KINDS`) -- so neither a malformed/hand-pasted
    entry nor a cmd: entry on a non-docs ticket (kind hand-edited after
    recording, or hand-pasted onto the wrong ticket) can ever validate.
    A cmd: entry on a disallowed kind is rejected outright here, never
    falling through to `_evidence_collected` (a `cmd:...` string could
    never coincidentally match a pytest node id anyway, but the explicit
    branch keeps the two evidence classes from ever being confused)."""
    if is_cmd_evidence(evidence):
        return ticket.kind in CMD_EVIDENCE_ALLOWED_KINDS
    return _evidence_collected(evidence, tests)


# frob:ticket T-0398
# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_scope_true_for_bound_test  # noqa: E501
def evidence_covers_scope(ticket: Ticket, snapshot: GraphSnapshot) -> bool:
    """D-02: whether at least one of `ticket`'s non-cmd evidence ids binds
    to a symbol/file under `ticket.scope`, via EITHER of two routes:

    1. A `TESTS` edge: walks the same `TESTS`-edge graph
       `frob.testing.select_tests` builds selections from, from the
       evidence side -- for each evidence id, find the `TESTS` edge whose
       test-side symref maps (via `_symref_to_nodeid`, honoring T-0137's
       either-direction `frob:tests` convention) to that id, and check
       whether the OTHER (source) side's file falls under `ticket.scope`.
    2. The evidence id's OWN file is directly inside `ticket.scope` --
       e.g. a ticket scoped to both its source AND its test file
       (`scope: [src/foo.py, tests/test_foo.py]`, this repo's own common
       convention, see T-0398's own ticket entry) needs no separate
       `frob:tests` directive for its evidence to count as covering: the
       human/agent already declared the test file itself in scope, which
       is exactly as strong a binding signal as a graph edge would be.

    Without either route, ANY collected pytest node id (however unrelated
    to the ticket) satisfies close/land -- `frob ticket evidence
    T-feature-x tests/test_logging.py::test_levels` closed T-feature-x
    just as well as a real covering test.

    A caller (today: `frob.app.ticket_runner`'s `_close`/`_land`, via
    `_covers_scope_for_ticket`/`_land_covers_scope_fn`; see
    `_done_transition_guard`'s `covers_scope` docstring for why it is
    injected rather than automatic) computes this against a
    `GraphSnapshot` and passes the result into
    `frob.tickets.transition`/`land`'s `covers_scope` parameter.

    A docs-kind ticket (T-0444) is exempt from the covering-TEST requirement:
    its scope is documentation/data files with no coverable code symbols, and
    T-0215 already sanctions it closing on a `--evidence-cmd` exit status. So
    a ticket whose kind permits cmd evidence (`CMD_EVIDENCE_ALLOWED_KINDS`,
    today just `docs`) and which carries at least one real cmd: evidence entry
    is considered covered. Code kinds cannot carry cmd evidence (enforced by
    `_transition_guard`/`_validate_closeable` against the same frozenset), so
    this can never loophole a bug/feature/security ticket into closing on an
    unrelated command."""
    if ticket.kind in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(evidence) for evidence in ticket.evidence
    ):
        return True
    return any(
        not is_cmd_evidence(evidence)
        and (
            _evidence_binds_to_scope(evidence, ticket.scope, snapshot)
            or scope_matches(evidence.split("::", 1)[0], ticket.scope)
        )
        for evidence in ticket.evidence
    )


def _evidence_binds_to_scope(
    evidence: str, scope: tuple[str, ...], snapshot: GraphSnapshot
) -> bool:
    """Whether `evidence` (a pytest/cargo node id) is the test-side of some
    `TESTS` edge whose source-side symbol's file is covered by `scope`."""
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        for test_side, source_side in (
            (edge.src, edge.target),
            (edge.target, edge.src),
        ):
            if _node_id_matches_symref(
                evidence, test_side
            ) and _file_of_symref_in_scope(source_side, scope):
                return True
    return False


def _node_id_matches_symref(evidence: str, symref: str) -> bool:
    """Whether `evidence` (a pytest/cargo node id) is the test named by
    `symref`: exact `_symref_to_nodeid` match (or its parametrize-expanded
    form), or -- for a bare test FILE symref with no `::` -- the file
    itself (or a path under it)."""
    if "::" not in symref:
        return evidence == symref or evidence.startswith(symref.rstrip("/") + "/")
    node_id = _symref_to_nodeid(symref)
    return evidence == node_id or evidence.startswith(node_id + "[")


def _file_of_symref_in_scope(symref: str, scope: tuple[str, ...]) -> bool:
    """Whether `symref`'s file (the part before `::`, or itself if bare)
    is covered by `scope` (`scope_matches`)."""
    path = symref.split("::", 1)[0]
    return scope_matches(path, scope)


# ---------------------------------------------------------------------------
# TESTS-edge indexing
# ---------------------------------------------------------------------------


def _test_edges(snapshot: GraphSnapshot, kind: str) -> dict[str, list[Edge]]:
    """`{target: [edges]}` for every TESTS edge of `kind`
    ("unit"/"integration"/"e2e")."""
    result: dict[str, list[Edge]] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS or edge.attrs.get("kind", "unit") != kind:
            continue
        result.setdefault(edge.target, []).append(edge)
    return result


def _unit_test_edges(snapshot: GraphSnapshot, kind: str) -> dict[str, list[Edge]]:
    """`{tested_symref: [edges]}` for every TESTS edge of `kind`, indexed by
    whichever endpoint names the tested symbol.

    Two `frob:tests` conventions coexist in this codebase (docs/modules/
    testing.md): a directive written above the SOURCE function names its
    covering test as `target` (`src` is the source symbol itself), and a
    directive written above/inside the TEST names what it covers as
    `target` (`src` is the test). `_test001_002_one` looks up coverage by
    the tested symbol's `record.symref`, which lands in `edge.src` for the
    first convention and `edge.target` for the second -- a single
    target-only (or src-only) index can only ever see one of the two,
    silently dropping the other convention's explicit edges to the
    naming-convention fallback (T-0336). Index both endpoints so a lookup
    matches regardless of which convention was used."""
    result: dict[str, list[Edge]] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS or edge.attrs.get("kind", "unit") != kind:
            continue
        result.setdefault(edge.target, []).append(edge)
        if edge.src != edge.target:
            result.setdefault(edge.src, []).append(edge)
    return result


# Extensions frob parses but does not (yet) run/collect executed test
# evidence for, so a `frob:tests` edge on one of them can never have its
# `src` land in `tests.node_ids`, no matter which file the directive
# itself lives in (T-0090). Rust was removed from this set by T-0092
# (`collect_rust_tests` gives real execution evidence via `tests.
# node_ids`), and TS was removed by T-0730 (`collect_ts_tests`'s vitest
# node ids are `path::name` symrefs -- the exact shape `_symref_to_nodeid`
# already produces from a TS `frob:tests` directive, so an exact/prefix
# match in `_node_id_collected` just works, same as python/rust).
#
# C/C++ stays in this set -- NOT an oversight, a disclosed gap (T-0730's
# Done report, T-0886). T-0886 investigated both candidate ctest-side
# routes and found neither `--show-only=json-v1`'s `backtrace` field
# (anchors to the CMake SCRIPT location of the `add_test()`/
# `gtest_discover_tests()` call, never the real test source, on every
# CMake version checked) nor a bare `--gtest_list_tests` (no source info
# at all) can answer source-accuracy on their own; `collect_cpp_tests`
# instead cross-references each test's executable (parsed straight out of
# `CTestTestfile.cmake`) against `compile_commands.json`
# (`_cpp_target_sources`) and upgrades to a real source-file node id
# whenever that target compiles from exactly one source file -- which
# `_edge_has_execution_evidence`'s existing `_node_id_collected` checks
# (run BEFORE this structural fallback, see `_edge_has_execution_evidence`
# above) already pick up automatically, no change needed here. C/C++
# stays in `_NATIVE_TEST_EXTENSIONS` because that upgrade only fires
# per-edge, when the project was configured with
# `CMAKE_EXPORT_COMPILE_COMMANDS=ON` and the matched target is
# unambiguous (a single compiled source file) -- most C/C++ edges still
# have no configured build directory (or an ambiguous/multi-source one)
# at gate-check time and still need this fallback; retiring it globally
# today would silently drop ALL of that TEST001-004 credit rather than
# tighten it.
_NATIVE_TEST_EXTENSIONS = frozenset({".c", ".h", ".cpp", ".hpp", ".cc", ".hh"})


def _is_native_test_src(src: str) -> bool:
    """True if `src`'s file extension has no execution-based test collector
    (see `_NATIVE_TEST_EXTENSIONS`); pytest is the only one frob runs."""
    path = src.split("::", 1)[0]
    return PurePosixPath(path).suffix.lower() in _NATIVE_TEST_EXTENSIONS


def _is_native_test_symref(src: str) -> bool:
    """True if `src`'s qualname follows a test-code convention this module
    already trusts elsewhere: a `tests` module/namespace segment (rust's
    `#[cfg(test)] mod tests { ... }`, mirroring `is_test_file`'s "tests" dir
    check) or a `test_`/`_test` leaf name (the C/C++ convention, mirroring
    `_is_test_path`'s python check). Extension alone (`_is_native_test_src`)
    only says "no execution collector exists"; this says "and it actually
    looks like test code" -- required together so a plain `frob:tests`
    directive on a non-test rust/c/cpp file (e.g. the target's own
    `lib.rs`) cannot rubber-stamp itself as evidence (T-0090 review)."""
    _, _, qualname = src.partition("::")
    if not qualname:
        return False
    parts = qualname.split(".")
    leaf = parts[-1]
    return "tests" in parts[:-1] or leaf.startswith("test_") or leaf.endswith("_test")


def _valid_edges(
    edges: list[Edge],
    tests: CollectedTests,
    snapshot: GraphSnapshot | None = None,
) -> list[Edge]:
    """Edges whose `src` is a collected pytest, cargo, vitest, or ctest node id
    (real execution evidence, `_symref_to_nodeid`), or -- for a language frob
    still has no SOURCE-ACCURATE execution-based test collector for (c/cpp,
    T-0090/T-0730) -- a `src` that both looks like test code
    (`_is_native_test_symref`) and resolves to a real bound symbol in
    `snapshot`.

    The comment DSL binds a `frob:tests` directive to its enclosing/following
    symbol regardless of which file it lives in relative to its target
    (`frob.graph.dsl.parse_directives`), so a directive whose src is a genuine
    c/cpp test function is structurally authoritative the moment it exists;
    frob just cannot (yet) prove the test actually ran the way it now can for
    python (`collect_python_tests`), rust (`collect_rust_tests`, T-0092), and
    TS (`collect_ts_tests`, T-0730). `snapshot` is optional so existing
    callers that only ever see python evidence are unaffected.

    Two `frob:tests` conventions coexist (see `_unit_test_edges`): `src` is
    the test and `target` is the tested symbol, or `src` is the tested
    symbol and `target` is the test. `e.src` is checked first (the
    convention this function originally assumed); `e.target` is checked as
    a fallback so a directive written above the SOURCE, naming its test as
    `target`, gets the same execution-evidence credit once `T-0336` makes
    `_test001_002_one` able to find it in the first place -- honoring that
    an edge exists (T-0336's fix) without also honoring what it actually
    proves would leave a real explicit binding permanently unable to clear
    TEST002, which is not "stricter," just wrong.
    """
    return [e for e in edges if _edge_has_execution_evidence(e, tests, snapshot)]


# frob:ticket T-0361
def _edge_has_execution_evidence(
    e: Edge,
    tests: CollectedTests,
    snapshot: GraphSnapshot | None,
) -> bool:
    """True if `e` has real execution evidence per the four checks `_valid_edges`
    applies in order (macro-file collection, src/target node-id match, or a
    native test symref bound in `snapshot`); split out of `_valid_edges` so
    that function stays a plain filter comprehension (T-0361)."""
    macro_file = _macro_symbol_file(e.src)
    if macro_file is not None:
        return _macro_file_collected(macro_file, tests.node_ids)
    if _node_id_collected(_symref_to_nodeid(e.src), tests.node_ids):
        return True
    if _node_id_collected(_symref_to_nodeid(e.target), tests.node_ids):
        return True
    return _edge_is_native_unverified(e, snapshot)


# frob:ticket T-0552
def _edge_is_native_unverified(e: Edge, snapshot: GraphSnapshot | None) -> bool:
    """True if `e`'s TEST001-004 credit rests solely on the c/cpp
    structural fallback (T-0090/T-0552/T-0730, docs/audits/gates-accounting.md B3):
    frob runs no collector that ever actually executes it -- `e.src` merely
    *looks like* test code by name/path and resolves in the graph. Split out
    of `_edge_has_execution_evidence` so `_test013_native_unverified` can
    identify exactly the edges receiving this weakest tier of credit,
    without duplicating the check."""
    return (
        snapshot is not None
        and _is_native_test_src(e.src)
        and _is_native_test_symref(e.src)
        and e.src in snapshot.symbols
    )


# frob:ticket T-0549
def _call_repr(node: ast.expr) -> str:
    """Best-effort source text of a `Call.func` node, for substring matching
    against assertion-style call names (`pytest.raises`, `self.assertEqual`,
    ...); returns "" rather than raising when a node shape `ast.unparse`
    cannot render (should not happen for real call targets, but this is a
    heuristic, not a parser, so it must never crash the gate over it)."""
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 - heuristic must never crash the gate
        return ""


# frob:ticket T-0549
def _function_asserts(node: ast.AST) -> bool:
    """True if `node` (a function/method body) contains an `assert`
    statement, a `raise`, or a call that looks like an assertion helper
    (`pytest.raises(...)`, `self.assertEqual(...)`, `np.testing.assert_*`,
    ...). A purely heuristic, static, name-based check -- it cannot know
    whether the call actually asserts anything meaningful, only whether the
    test function contains ANY assertion-shaped construct at all, which is
    exactly what a no-op body (`pass`, or a body that only computes and
    discards a value) lacks."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assert):
            return True
        if isinstance(sub, ast.Raise):
            return True
        if isinstance(sub, ast.Call):
            call_repr = _call_repr(sub.func).lower()
            if "raises" in call_repr or "assert" in call_repr:
                return True
    return False


# frob:ticket T-0949
@functools.lru_cache(maxsize=4096)
def _parsed_test_module(
    root_str: str, file_path: str, mtime_ns: int, size: int
) -> ast.Module | None:
    """`ast.parse()` of `root_str/file_path`, memoized on `(file_path,
    mtime_ns, size)` so re-reading/re-parsing the SAME test file (common:
    many test functions per file, each independently checked by
    `_has_assertion_evidence`) costs one real parse, not one per call
    (T-0949 -- `test_gate`'s isolated-call cProfile showed `ast.parse`/
    `compile` as the single largest remaining cost after the two
    `_snake()`/node-id-scan fixes landed alongside this one). Keying on
    `mtime_ns`/`size` rather than just the path means a file edited
    mid-process (a long-lived `frob serve` sesssion, or a test suite that
    rewrites its own fixture between gate runs) transparently misses the
    cache and reparses, instead of serving stale content silently -- no
    explicit invalidation call needed, unlike a plain path-keyed cache
    would require. Returns `None` on any read/parse failure, exactly the
    conditions `_has_assertion_evidence` already treated as fail-open."""
    try:
        source = Path(root_str, file_path).read_text(encoding="utf-8")
        return ast.parse(source)
    except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
        return None


# frob:ticket T-0549
def _has_assertion_evidence(root: Path, base_node_id: str) -> bool:
    """True if the python test function named by `base_node_id` (a
    `path::[Class::]function` pytest node id, no `[case-id]` suffix)
    contains an assertion-shaped construct (`_function_asserts`).

    Fails OPEN (returns True) whenever the check cannot be performed at all:
    `base_node_id` does not name a `.py` file, the file cannot be read, the
    source does not parse, or no function by that name is found in it. This
    keeps the heuristic strictly additive -- it can only ever REMOVE bogus
    case-count credit from a python test whose body was actually inspected
    and found empty of assertions, never penalize a case this check could
    not evaluate (native/non-python tests, synthetic test fixtures in unit
    tests that reference files never written to disk, and so on).

    T-0949: the read+parse itself is delegated to `_parsed_test_module`,
    memoized per file so N functions checked in the same file cost one
    parse total instead of N."""
    parts = base_node_id.split("::")
    if len(parts) < 2 or not parts[0].endswith(".py"):
        return True
    file_path, func_name = parts[0], parts[-1]
    try:
        stat = (root / file_path).stat()
    except OSError:
        return True
    tree = _parsed_test_module(str(root), file_path, stat.st_mtime_ns, stat.st_size)
    if tree is None:
        return True
    found = False
    try:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name != func_name:
                    continue
                found = True
                if _function_asserts(node):
                    return True
    except Exception:  # noqa: BLE001 - heuristic must fail open, never crash the gate
        return True
    return not found


# frob:ticket T-0307
def _case_count(
    valid_edges: list[Edge], tests: CollectedTests, root: Path | None = None
) -> int:
    """Total collected case count for edges already validated by `_valid_edges`.

    `_valid_edges` answers "does this directive have any execution
    evidence at all" (one bool per edge), which is right for TEST001 but
    wrong for TEST002/TEST003's minimum-case counts: a `frob:tests`
    directive bound to a `@pytest.mark.parametrize`-decorated function (or
    a cargo test macro that expands similarly) validates via exactly one
    prefix match in `_node_id_collected`, so `len(valid_edges)` reports 1
    case no matter how many parametrize variants actually collected --
    undercounting a genuinely well-tested symbol and forcing three sibling
    repos (lograder, aprog-public, feldspar) to write dishonest
    non-parametrized twin tests to clear the gate (T-0307). This instead
    re-counts each edge's *actual* collected node ids: the exact node id
    if present, plus every `base[case-id]` parametrize expansion, each
    counted as its own case. An edge with no execution-based node-id match
    at all (the c/cpp structural fallback in `_valid_edges`, which has
    no pytest/cargo/vitest/ctest evidence to expand) still counts as
    exactly one case, matching its previous `len(valid_edges)` contribution.

    T-0549: that per-case counting is exactly what makes
    `@pytest.mark.parametrize(range(10))` over a test body with NO
    assertions at all inflate to 10 "cases", clearing a `min_unit_cases`/
    `min_integration`/`min_design_e2e` floor a genuinely tested symbol
    would need real coverage to reach. When `root` is given, a python
    edge with more than one collected variant is capped back to exactly 1
    case UNLESS `_has_assertion_evidence` finds an actual assertion-shaped
    construct in the test body -- a real parametrized test (T-0307's own
    fixture) still counts every variant; a no-op one is capped like the
    structural fallback, not zeroed (fitting neither this function's
    other cases). `root=None` (the direct-unit-test default) skips the
    check entirely and preserves the pre-T-0549 count, so callers that
    have no filesystem root to check against (or tests exercising this
    function directly against node ids with no file on disk) are
    unaffected.
    """
    total = 0
    for edge in valid_edges:
        macro_file = _macro_symbol_file(edge.src)
        if macro_file is not None:
            # T-0318: a macro stand-in has no exact/prefix node id of its
            # own (proptest's expansion names each case after its OWN fn,
            # never after the macro) -- count every collected case under
            # the same file instead, `_valid_edges` already proved >=1.
            file_prefix = f"{macro_file}::"
            total += sum(
                1 for node_id in tests.node_ids if node_id.startswith(file_prefix)
            )
            continue
        base = _symref_to_nodeid(edge.src)
        # T-0949: `_case_ids_by_base` memoizes the base->case-ids grouping
        # once per `tests.node_ids` value instead of this re-scanning the
        # full node-id set with `startswith()` for every edge.
        matches = (1 if base in tests.node_ids else 0) + len(
            _case_ids_by_base(tests.node_ids).get(base, ())
        )
        if root is not None and matches > 1 and not _has_assertion_evidence(root, base):
            matches = 1
        total += matches if matches else 1
    return total


# frob:ticket T-0018
def _inferred_unit_cases(symref: str, tests: CollectedTests) -> int:
    """Count collected tests that cover `symref` by NAMING CONVENTION.

    A `frob:tests` directive is authoritative, but requiring one on every
    function is friction. So a public function `foo` (or method `Cls.foo`)
    is also considered unit-tested by any collected node id whose test
    name, snake-cased, contains the symbol's snake-cased name -- e.g.
    `test_foo`, `test_foo_handles_empty`, `TestFoo::test_x`. Conservative:
    it only counts, never invents an edge, and the symbol name must be a
    whole `_`-delimited token in the test id so `add` does not match
    `readd`.
    """
    _, _, qualname = symref.partition("::")
    leaf = _snake(qualname.rsplit(".", 1)[-1])
    if len(leaf) < 3:  # too-short names (a, id, of) match everything
        return 0
    token = re.compile(rf"(^|[^a-z0-9]){re.escape(leaf)}([^a-z0-9]|$)")
    # T-0949: `_leaf_snake_index` memoizes each node id's `_snake()`'d leaf
    # ONCE per `tests` value instead of recomputing it on every call to
    # this function (which happens once per unbound public symbol).
    return sum(
        1 for _, node_leaf in _leaf_snake_index(tests) if token.search(node_leaf)
    )


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------


# frob:enforces CHK-GATE-DRIFT001
def _drift001(report, snapshot: GraphSnapshot) -> list[Violation]:  # noqa: ANN001
    """DRIFT001: an acked doc facet's digest moved since the ack."""
    violations: list[Violation] = []
    for stale in report.stale:
        record = snapshot.symbols.get(stale.entry.ref)
        line = record.span[0] if record is not None else 0
        file = stale.entry.ref.split("::", 1)[0]
        _log.debug("DRIFT001: %s facet=%s moved", stale.entry.ref, stale.entry.facet)
        violations.append(
            Violation(
                rule="DRIFT001",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DRIFT001: {stale.entry.ref} ({stale.entry.facet}) digest moved "
                    f"since ack ({len(stale.dependents)} dependent(s)); "
                    f"run: frob ack {stale.entry.ref}"
                ),
            )
        )
    return violations


# frob:enforces CHK-GATE-DRIFT002
def _drift002(report) -> list[Violation]:  # noqa: ANN001
    """DRIFT002: an edge endpoint no longer resolves to a live symbol."""
    violations: list[Violation] = []
    for dangling in report.dangling:
        file, line = _site_from_edge_origin(dangling.edge.origin)
        candidates = ", ".join(dangling.candidates) or "no candidates found"
        _log.debug("DRIFT002: %s -> %s gone", dangling.edge.src, dangling.edge.target)
        violations.append(
            Violation(
                rule="DRIFT002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DRIFT002: {dangling.edge.kind.value} edge "
                    f"{dangling.edge.src} -> {dangling.edge.target} no longer "
                    f"resolves; candidates: {candidates}; fix the reference or "
                    f"run: frob ack <candidate>"
                ),
            )
        )
    return violations


# frob:doc docs/modules/gates.md#public-api
def drift_gate(snapshot: GraphSnapshot, lock: LockFile) -> tuple[Violation, ...]:
    """DRIFT001 (stale ack) and DRIFT002 (dangling edge endpoint)."""
    report = _graph_drift(lock, snapshot)
    return (*_drift001(report, snapshot), *_drift002(report))


# ---------------------------------------------------------------------------
# Digest-drift (AFFECT001/AFFECT002): T-0325's cut enforcement half, T-0628
# ---------------------------------------------------------------------------


def _affect_ref_file(ref: str) -> str:
    """The file path a doc-anchor (`path#anchor`) or symref (`path::qualname`)
    string is rooted in -- the common split `affects()`'s two id shapes need
    to answer "was this file touched in the diff"."""
    if "#" in ref:
        return ref.split("#", 1)[0]
    return ref.split("::", 1)[0]


def _affect001_violation(
    ref: str, file: str, line: int, stale_docs: list[str]
) -> Violation:
    """AFFECT001: a touched symbol's `affects()` closure names doc anchor(s)
    whose file was not touched in the same diff -- the CLAUDE.md north-star
    enforcement half `docs/modules/graph.md#affects` left as future work."""
    return Violation(
        rule="AFFECT001",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"AFFECT001: {ref} changed but its affects()-closure doc(s) "
            f"{', '.join(sorted(stale_docs))} were not touched in this diff; "
            f"run: frob graph affects {ref}"
        ),
    )


def _affect002_violation(
    ref: str, file: str, line: int, stale_deps: list[str]
) -> Violation:
    """AFFECT002: a touched symbol's `affects()` closure names dependent
    symbol(s) (`uses-contract`) whose file was not touched in the same
    diff -- the code half of the same enforcement gap AFFECT001 covers."""
    return Violation(
        rule="AFFECT002",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"AFFECT002: {ref} changed but its affects()-closure "
            f"dependent(s) {', '.join(sorted(stale_deps))} were not touched "
            f"in this diff; run: frob graph affects {ref}"
        ),
    )


# frob:doc docs/modules/gates.md#affect001-affect002-t-0628
# frob:ticket T-0628
# frob:tests tests/test_gates_affect_drift.py::TestAffectDriftGate.test_stale_dependent_doc_flagged  # noqa: E501
# frob:tests tests/test_gates_affect_drift.py::TestAffectDriftGate.test_stale_dependent_code_flagged  # noqa: E501
# frob:tests tests/test_gates_affect_drift.py::TestAffectDriftGate.test_clean_when_closure_also_touched  # noqa: E501
# frob:tests tests/test_gates_affect_drift.py::TestAffectDriftGate.test_no_closure_is_silent  # noqa: E501
# frob:enforces CHK-GATE-AFFECT001
# frob:enforces CHK-GATE-AFFECT002
def affect_drift_gate(snapshot: GraphSnapshot, diff: Diff) -> tuple[Violation, ...]:
    """AFFECT001/AFFECT002 (T-0628, T-0325 follow-on): for every symbol this
    diff touches, walk its `frob.graph.affects.affects()` closure and FAIL
    when a dependent doc anchor (AFFECT001) or dependent symbol's file
    (AFFECT002) was NOT also touched in the same diff -- the enforcement
    half of the CLAUDE.md north-star ("a graph of what documentation and
    what other code needs to be updated whenever something is touched")
    that `docs/modules/graph.md#affects` (T-0325) explicitly cut as future
    work. Symbols with an empty `affects()` closure (no `uses-contract`
    dependents, no doc/test edges) are silent -- there is nothing to have
    drifted. A symbol whose closure was truncated (`max_depth`/`max_nodes`)
    is still checked against the (possibly partial) dependents/docs actually
    visited; a truncated closure under-reports rather than false-positiving.
    """
    touched = _touched_symrefs(diff, snapshot)
    touched_files = _touched_files(diff)
    violations: list[Violation] = []
    for ref in sorted(touched):
        aff = _graph_affects(snapshot, ref)
        if not aff.dependents and not aff.docs:
            continue
        record = snapshot.symbols.get(ref)
        file = ref.split("::", 1)[0]
        line = record.span[0] if record is not None else 0
        stale_docs = [d for d in aff.docs if _affect_ref_file(d) not in touched_files]
        stale_deps = [
            dep for dep in aff.dependents if _affect_ref_file(dep) not in touched_files
        ]
        if stale_docs:
            _log.debug("AFFECT001: %s stale docs=%s", ref, stale_docs)
            violations.append(_affect001_violation(ref, file, line, stale_docs))
        if stale_deps:
            _log.debug("AFFECT002: %s stale dependents=%s", ref, stale_deps)
            violations.append(_affect002_violation(ref, file, line, stale_deps))
    return tuple(violations)


# ---------------------------------------------------------------------------
# Coverage: COV001..COV004 and TODO001/TODO002
# ---------------------------------------------------------------------------


# frob:ticket T-0550
def _diff_load_failed_violation(rule: str, base: str) -> Violation:
    """T-0550/B8: `rule`'s blocking violation for a diff that FAILED to
    load (bad `--base`, no merge-base, detached HEAD, git failure) --
    distinct from a genuinely empty/clean diff, which correctly clears
    `rule` with no violation at all. `_load_diff` degrades a failed
    `working_diff` to an empty `Diff` so the rest of the gates run does
    not hard-crash, but COV002/SCOPE001/TODO001 are diff-driven gates that
    treat "no touched symbols" as "nothing to enforce" -- so that same
    degrade, unflagged, silently passed all three on a real failure
    (committing on `main` with the default base, or any bad `--base`,
    zeroed the touched set and cleared every diff-driven gate). This is
    fired instead, loud and blocking, whenever the diff genuinely failed to
    load rather than genuinely being empty.
    """
    return Violation(
        rule=rule,
        severity=Severity.ERROR,
        file="",
        line=0,
        message=(
            f"{rule}: working diff against base={base!r} failed to load "
            f"(bad --base, detached HEAD, or a git failure); {rule} cannot "
            "be evaluated -- this is a load failure, not a clean/empty "
            "diff, so it is not silently passing"
        ),
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0550
# frob:ticket T-0719
def coverage_gate(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    diff: Diff,
    tests: CollectedTests,
    active_ticket: str | None = None,
    diff_load_failed: bool = False,
    diff_load_no_repo: bool = False,
    python_collection_failed: str | None = None,
) -> tuple[Violation, ...]:
    """COV001..COV007, PLACE001, and TODO001/TODO002/TODO003.

    `root` (repo root, T-0233) lets COV001 tell a *resolving* `frob:doc`
    edge apart from a broken one -- see `_resolved_documented_srcs`.
    `active_ticket` (T-0542/B10) lets COV002 prefer the ticket actually
    being worked over any other open ticket whose scope happens to also
    cover the same file. `diff_load_failed` (T-0550/B8) is `True` only when
    `diff` is `_load_diff`'s empty placeholder for a genuine `working_diff`
    failure, never for an honestly clean tree; when set, COV002 and
    TODO001 (both diff-driven, both otherwise silently satisfied by an
    empty diff) are replaced with one loud `_diff_load_failed_violation`
    each instead of being evaluated against a diff known to be bogus.
    TODO003 (T-0783) is, like TODO002, repo-wide rather than diff-scoped
    (see `_todo003_long_deferred`), so it runs unconditionally rather than
    branching on `diff_load_failed`.

    T-0719: `diff_load_no_repo` narrows `diff_load_failed` further -- `True`
    only when the load failed because `root` is not inside a git repository
    at ALL (`_load_diff`'s `NotARepo`-shaped case), as opposed to a real
    repo whose `working_diff` genuinely failed (bad `--base`, detached
    HEAD). A genuinely git-less root is treated the same as a clean/empty
    diff here -- there is structurally no touched set to enforce against,
    so COV002/TODO001 evaluate normally (against the empty diff, finding
    nothing) instead of firing the loud `_diff_load_failed_violation`.

    T-1161: `python_collection_failed`, when not `None` (`frob.testing.
    python_collection_failure_detail()`'s captured text, threaded through
    `run_gates`' `_load_tests`), replaces `_cov003`'s normal per-evidence
    sweep with ONE `_python_collection_failed_violation` -- the 2026-07-28
    incident where a broken venv shim degraded into 6219 independently
    "unresolved" COV003s instead of naming the one real collector failure.
    """
    violations: list[Violation] = []
    violations.extend(_cov001(root, snapshot))
    if diff_load_failed and not diff_load_no_repo:
        violations.append(_diff_load_failed_violation("COV002", diff.base))
    else:
        violations.extend(_cov002(snapshot, queue, diff, active_ticket))
    if python_collection_failed is not None:
        violations.append(_python_collection_failed_violation(python_collection_failed))
    else:
        violations.extend(_cov003(queue, tests))
    violations.extend(_cov004(queue))
    violations.extend(_cov005(root, snapshot, diff))
    violations.extend(_cov006(root, snapshot))
    violations.extend(_cov007(snapshot))
    violations.extend(_place001(root, snapshot))
    if diff_load_failed and not diff_load_no_repo:
        violations.append(_diff_load_failed_violation("TODO001", diff.base))
    else:
        violations.extend(_todo001(snapshot, queue, diff))
    violations.extend(_todo003_long_deferred(root, snapshot, queue))
    return tuple(violations)


def _resolved_documented_srcs(root: Path, snapshot: GraphSnapshot) -> set[str]:
    """Symrefs carrying a `frob:doc` edge whose anchor actually resolves.

    T-0233: a `frob:doc <file>#<slug>` edge with a nonexistent file or an
    unresolved anchor is already its own DOC002 error (`docanchor_gate`);
    that error must not ALSO count as satisfying the symbol's COV001
    documentation obligation. Before this fix a broken edge quietly
    satisfied `_documented_srcs`, so `_cov001` skipped the symbol entirely
    -- one bad `frob:doc` line silently masked real missing-coverage
    findings for every other broken edge on the same file. Reuses
    `_docanchor_check_edge`'s own resolution logic (memoized per doc file
    via a fresh `slug_cache`) so the two gates can never disagree about
    what "resolves" means.
    """
    slug_cache: dict[str, Option[set[str]]] = {}
    resolved: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.DOC:
            continue
        if _docanchor_check_edge(root, edge, slug_cache) is None:
            resolved.add(edge.src)
    return resolved


# frob:ticket T-0553
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov001_waiver_does_not_blanket_suppress_sibling_symbol  # noqa: E501
# frob:enforces CHK-GATE-COV001
# frob:enforces CHK-THEME-PYTHON-ONLY
# frob:enforces CHK-SUBSYS-LANG-CHECK-DOCS
def _cov001(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """COV001: a public symbol has no explicit, *resolving* `frob:doc` edge.

    A docstring is not enough -- the obligation is an explicit `frob:doc
    <docs/anchor>` directive tying the symbol to a doc page whose drift is
    then tracked. Explicit edges are the point: they are what DRIFT001 can
    check. A `frob:doc` edge that fails to resolve (DOC002) does not count
    as documentation (T-0233) -- see `_resolved_documented_srcs`. A file
    carrying a recognized generated-file marker (T-0234,
    `frob.graph._generated.is_generated_source`) is exempt outright: nobody
    hand-documents machine-generated code, but unlike `[graph] exclude` the
    file stays IN the graph so xref/dup/arch still see its symbols. The
    per-path result is memoized (`generated_cache`) since a file's symbols
    are visited consecutively and re-reading the same header per symbol
    would otherwise multiply file IO by symbol count.
    """
    documented = _resolved_documented_srcs(root, snapshot)
    generated_cache: dict[str, bool] = {}
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.symref in documented:
            continue
        if _is_test_path(record.id.path):
            continue
        path = record.id.path
        if path not in generated_cache:
            generated_cache[path] = is_generated_source(root, path)
        if generated_cache[path]:
            _log.debug(
                "COV001: %s skipped -- %s is a generated source", record.symref, path
            )
            continue
        _log.debug("COV001: %s public with no frob:doc edge", record.symref)
        violations.append(
            Violation(
                rule="COV001",
                severity=Severity.WARN,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"COV001: {record.symref} is public with no frob:doc edge; "
                    f"add: frob:doc <docs/anchor> above it"
                ),
                # T-0553 (B11): COV001 is precisely about ONE symbol (this
                # `record`), so set `symref` to get `_match_waiver`'s
                # symbol-exact matching -- without it, one `frob:waive
                # COV001` anywhere in the file blanket-suppresses every
                # other undocumented public symbol in that file, which is
                # not what a targeted waiver author intends.
                symref=record.symref,
            )
        )
    return tuple(violations)


# frob:ticket T-0965
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff  # noqa: E501
def _open_scopes(
    queue: TicketQueue, root: str | None = None, diff: Diff | None = None
) -> list[tuple[str, tuple[str, ...]]]:
    """`(ticket_id, scope)` for every open ticket that declares a scope,
    PLUS (T-0965 grace, mirroring `_bound_to_open_ticket`'s T-0214/T-0320/
    T-0590 edge-based grace window) a `DONE` ticket whose declared scope
    is otherwise unaccounted for, when its own close transition is landing
    within this same uncommitted `diff`'s `tickets.md` hunk(s) AND its
    state at `diff.base` permits grace (open, or nonexistent -- see
    `_base_state_permits_grace`).

    Without this, a ticket that covered a whole file/module by SCOPE
    (rather than a per-symbol `frob:ticket` edge) stops covering any of its
    symbols the instant it closes to `DONE` -- even though its own closing
    commit is still sitting, unlanded, in the very same diff COV002
    evaluates. `root`/`diff` are optional (default `None`, no grace
    extension) so existing callers that only care about open-ticket scope
    (e.g. tests exercising `_scope_covers` directly) are unaffected."""
    result = [
        (t.id, t.scope)
        for t in queue.tickets.values()
        if t.state in _OPEN_STATES and t.scope
    ]
    if root is not None and diff is not None:
        base_states = _ledger_states_at_base(root, diff.base)
        result.extend(
            (t.id, t.scope)
            for t in queue.tickets.values()
            if t.scope
            and t.state == TicketState.DONE
            and _ticket_marker_in_diff_hunk(root, diff, t.id)
            and _base_state_permits_grace(base_states.get(t.id))
        )
    return result


# frob:ticket T-0542
def _scope_glob_specificity(path: str, scope: tuple[str, ...]) -> int:
    """The length of the longest literal (pre-wildcard) prefix among
    `scope`'s expanded globs that actually match `path` -- how specific a
    ticket's scope claim on `path` is (B10). `-1` if nothing in `scope`
    matches `path` at all."""
    best = -1
    for glob in _scope_globs(_split_scope_entries(scope)):
        if not fnmatch.fnmatch(path, glob):
            continue
        prefix_len = len(glob.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0])
        best = max(best, prefix_len)
    return best


# frob:ticket T-0542
def _scope_covers(
    path: str,
    open_scopes: list[tuple[str, tuple[str, ...]]],
    active_ticket: str | None = None,
) -> bool:
    """True if `path` is unambiguously covered by an open ticket's scope
    (B10). Prefers `active_ticket`'s own scope first when it covers `path`.
    Otherwise, when exactly one open ticket's scope matches, that single
    match covers it -- but when MULTIPLE open tickets' scopes all cover the
    same path, the broadest first-match-wins behavior this replaces let any
    one of them (e.g. a `src/frob/**` catch-all) silently vouch for symbols
    it has nothing to do with. Now the narrowest (most specific) matching
    scope wins only when it is the UNIQUE narrowest match; a genuine tie
    (two open tickets whose scopes are equally specific over `path`) is
    ambiguous and does NOT cover -- an explicit `frob:ticket` edge is
    required instead."""
    covering = [tid for tid, scope in open_scopes if scope_matches(path, scope)]
    if not covering:
        return False
    if active_ticket is not None and active_ticket in covering:
        return True
    if len(covering) == 1:
        return True
    scored = sorted(
        (
            (_scope_glob_specificity(path, scope), tid)
            for tid, scope in open_scopes
            if tid in covering
        ),
        reverse=True,
    )
    best_score = scored[0][0]
    winners = [tid for score, tid in scored if score == best_score]
    if len(winners) > 1:
        _log.debug(
            "COV002: %s ambiguously covered by %d equally-specific open "
            "ticket scopes %s; not covered, needs an explicit frob:ticket edge",
            path,
            len(winners),
            winners,
        )
        return False
    return True


def _ticket_edges(snapshot: GraphSnapshot, symref: str) -> list[Edge]:
    """The `frob:ticket` edges anchored on `symref`."""
    return [e for e in edges_from(snapshot, symref) if e.kind == EdgeKind.TICKET]


# frob:ticket T-0214
# frob:ticket T-0320
# frob:ticket T-0590
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_done_ticket_covers_own_closing_diff  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_done_ticket_without_grace_still_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_marker_touch_without_state_transition_still_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_grace_covers_ticket_created_and_closed_in_same_diff  # noqa: E501
def _bound_to_open_ticket(
    snapshot: GraphSnapshot, queue: TicketQueue, symref: str, diff: Diff | None = None
) -> bool:
    """True if `symref` has a `frob:ticket` edge to an open ticket, OR (T-0214
    grace window, T-0320 tightened, T-0590 widened) to a ticket whose OWN
    close is landing to `DONE` within this same uncommitted `diff`'s
    `tickets.md` hunk(s) AND whose state at the diff's base commit was
    either open or nonexistent (see `_base_state_permits_grace`).

    Closing the covering ticket and landing the symbol edit it covers is one
    logical change; if THIS ticket's `<!-- ticket:T-#### -->` marker falls
    inside a touched `tickets.md` hunk, the close has not yet become a
    separate, already-landed commit, so it is not a genuine coverage gap for
    COV002 to flag -- see `_cov002`'s docstring. A bare "tickets.md is
    touched somewhere in the diff" is not enough: that would grant grace to
    any already-`DONE` ticket's stale edge whenever the diff happens to
    close a *different* ticket, which is a bypass, not a catch-22 fix (see
    `_ticket_marker_in_diff_hunk`). Marker-in-hunk alone is still only a
    PROXY for "closing" (T-0320): a typo fix, evidence append, or reformat
    inside an already-`DONE` ticket's section also touches its marker line
    without ever transitioning it, so grace additionally requires the
    ticket's state at `diff.base` (before this diff) to have been open OR
    the ticket to not have existed at `diff.base` at all -- see
    `_ledger_states_at_base` and `_base_state_permits_grace`. The latter
    (T-0590) matters for a ticket created AND closed entirely within the
    current uncommitted work (a `frob ticket new` + close cycle that has
    not yet landed to `main`): it has no `tickets.md` entry at base, so
    without this widening its own close would be wrongly treated as a
    stale pre-existing `DONE` edge instead of the genuine same-diff
    transition it is. Once the close lands as its own commit (tickets.md
    drops out of the diff, the hunk no longer spans this ticket's marker,
    or the ticket was already `DONE` at `diff.base`), a `DONE` ticket's
    edge stops counting here, same as before, so a truly unrelated later
    touch to the symbol is still caught.
    """
    for edge in _ticket_edges(snapshot, symref):
        ticket = queue.tickets.get(edge.target)
        if ticket is None:
            continue
        if ticket.state in _OPEN_STATES:
            return True
        # T-1053: PERF008's waiver here was retired -- `EffectGraph.
        # callee_is_memoized` now recognizes `_ledger_states_at_base`'s own
        # `@functools.lru_cache(maxsize=32)` decorator and suppresses this
        # finding at the source instead of requiring a waiver.
        if (
            diff is not None
            and ticket.state == TicketState.DONE
            and _ticket_marker_in_diff_hunk(snapshot.root, diff, ticket.id)
            and _base_state_permits_grace(
                _ledger_states_at_base(snapshot.root, diff.base).get(ticket.id)
            )
        ):
            return True
    return False


# frob:ticket T-0590
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_grace_covers_ticket_created_and_closed_in_same_diff  # noqa: E501
def _base_state_permits_grace(state_at_base: TicketState | None) -> bool:
    """True if a ticket's state at the diff's base commit is consistent with
    a genuine open -> DONE transition happening WITHIN this diff, including
    the ticket not existing at base at all.

    T-0590: a ticket entirely created AND closed since diverging from the
    diff's base (e.g. `frob ticket new` + work + `frob ticket close`, all
    uncommitted relative to `main`, or landed as separate commits on a
    worktree branch that has not itself landed to `main` yet) has NO entry
    in `tickets.md` at base -- `_ledger_states_at_base` correctly returns
    `None` for it, since the ticket did not exist there. The pre-T-0590
    check required `state_at_base in _OPEN_STATES`, which `None` fails,
    wrongly treating "never existed at base" the same as "already closed
    before this diff" -- both denied grace, even though a nonexistent
    ticket obviously cannot be a stale, already-landed DONE edge (T-0320's
    actual concern). Any ticket count `!= DONE` at base (open, or absent)
    proves the transition to DONE genuinely happened in this diff;
    `DROPPED` is excluded because a DROPPED -> DONE transition is not a
    real closing-diff shape this grace window is meant to cover.
    """
    return state_at_base != TicketState.DONE and state_at_base != TicketState.DROPPED


@functools.lru_cache(maxsize=32)
def _ledger_states_at_base(root: str, base: str) -> Mapping[str, TicketState]:
    """The `tickets.md` ticket-id -> state map as it existed at `diff.base`
    (the merge-base sha), or `{}` if `tickets.md` did not exist there or
    failed to parse.

    T-0320: `_bound_to_open_ticket`'s marker-in-hunk grace is a PROXY for "a
    ticket close is landing in this diff" -- it does not by itself prove a
    state TRANSITION, so any touch to an already-`DONE` ticket's marker line
    (typo fix, evidence append, reformat) would otherwise grant grace to a
    stale, uncovered symbol. Fetching the ledger as it stood before this
    diff and requiring the ticket to have been open there closes that gap:
    grace now demands an actual open -> DONE transition, not mere hunk
    overlap. Cached per `(root, base)` since `_cov002` calls this once per
    touched symbol and the base ledger does not change mid-run.
    """
    spawned = run_argv(("git", "-C", root, "show", f"{base}:tickets.md"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.debug(
            "_ledger_states_at_base: no tickets.md at base=%s (root=%s)", base, root
        )
        return {}
    parsed = _tickets_parse_ledger(spawned.danger_ok.stdout)
    if parsed.is_err:
        _log.debug(
            "_ledger_states_at_base: unparsable tickets.md at base=%s: %s",
            base,
            parsed.danger_err,
        )
        return {}
    return {tid: t.state for tid, t in parsed.danger_ok.items()}


# frob:ticket T-0564
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_grace_matches_hunk_anywhere_in_ticket_block  # noqa: E501
def _ticket_marker_in_diff_hunk(root: str, diff: Diff, ticket_id: str) -> bool:
    """True if any of `diff`'s `tickets.md` hunk spans overlaps `ticket_id`'s
    whole YAML block (from its `<!-- ticket:<ticket_id> -->` marker line
    through the block's closing ` ``` ` fence), not just the exact marker
    line.

    This is the T-0214-bypass fix (scope a hunk to the specific ticket
    whose close is actually present, not merely "some" hunk existing in
    `tickets.md`), tightened by T-0564: a ticket's own state transition
    (e.g. `state: queued -> done`) or an evidence-list insertion typically
    lands several lines below the marker/id/title lines, inside the same
    YAML block -- a hunk covering only that later line would miss the
    marker-line-only check and wrongly deny grace to a ticket whose own
    closing diff plainly IS present. Matching anywhere in the block span
    keeps the "unrelated ticket's stale edge doesn't ride along" guarantee
    (a hunk elsewhere in `tickets.md`, outside this ticket's block, still
    does not count) while covering the whole block, not one line of it.
    """
    tickets_md_hunks = [h for h in diff.hunks if h.file == "tickets.md"]
    if not tickets_md_hunks:
        return False
    tickets_md_path = Path(root) / "tickets.md"
    if not tickets_md_path.is_file():
        return False
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = tickets_md_path.read_text(encoding="utf-8").splitlines()
    block_start: int | None = None
    block_end: int | None = None
    for idx, line in enumerate(lines):
        if marker in line:
            block_start = idx + 1  # 1-indexed line number of the marker
            for fence_idx in range(idx + 1, len(lines)):
                if lines[fence_idx].strip() == "```":
                    block_end = fence_idx + 1  # 1-indexed closing fence line
                    break
            break
    if block_start is None:
        return False
    if block_end is None:
        block_end = len(lines)
    for hunk in tickets_md_hunks:
        start, end = hunk.span
        if max(start, block_start) <= min(end, block_end):
            return True
    return False


def _strata_module_symref(record_id_path: str, qualname: str) -> str | None:
    """The owning `module`'s symref for a `.strata` declaration's `qualname`.

    `_walk_strata.py` qualifies every non-module declaration as
    `<module_name>.<ident>` (one level of nesting, never deeper); this
    strips the trailing `.<ident>` to recover the module's own symref, or
    returns `None` for a bare (module-less, or the module decl itself)
    qualname that has nothing to strip.
    """
    if not record_id_path.endswith(".strata"):
        return None
    if "." not in qualname:
        return None
    module_qualname = qualname.rsplit(".", 1)[0]
    return f"{record_id_path}::{module_qualname}"


def _covered_by_strata_module(
    snapshot: GraphSnapshot, queue: TicketQueue, symref: str, diff: Diff
) -> bool:
    """True if a `.strata` declaration's owning `module` carries the
    `frob:ticket` edge, so each nested `node`/`flow`/`assert`/... need not
    repeat it.

    A `.strata` file is one design artifact (T-0164): a single directive on
    the `module` block covers everything nested under it, the same
    blast-radius reasoning `_scope_covers` already applies at the file
    level, just one notch finer so a `.strata` file sharing a ticket with
    unrelated files does not have to bind every declaration by hand.
    """
    record = snapshot.symbols[symref]
    module_symref = _strata_module_symref(record.id.path, record.id.qualname)
    if module_symref is None or module_symref not in snapshot.symbols:
        return False
    return _bound_to_open_ticket(snapshot, queue, module_symref, diff)


def _cov002(
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    diff: Diff,
    active_ticket: str | None = None,
) -> tuple[Violation, ...]:
    """COV002: a changed symbol is accounted for by neither a `frob:ticket`
    edge to an open ticket NOR an open ticket whose declared `scope` covers
    its file NOR (for `.strata` declarations only) its owning `module`.

    Scope coverage means a cohesive refactor is acknowledged once (the
    ticket's scope glob) instead of demanding a per-symbol directive on
    every function it touches -- the same blast-radius the scope gate
    already enforces, read the other direction. `.strata` module coverage
    (T-0164) applies that same reasoning one level down: a `.strata` file
    is one design artifact, so a `frob:ticket` on its `module` declaration
    covers every `node`/`flow`/`assert`/... nested inside it instead of
    demanding a copy-pasted directive per declaration. A closed ticket also
    covers its own closing diff (T-0214): see `_bound_to_open_ticket`'s
    grace-window docstring for why that is not a genuine gap.
    """
    open_scopes = _open_scopes(queue, snapshot.root, diff)
    touched = sorted(_touched_symrefs(diff, snapshot))
    violations = [
        v
        for symref in touched
        for v in (
            _cov002_check_symref(
                snapshot, queue, symref, open_scopes, diff, active_ticket
            ),
        )
        if v is not None
    ]
    return tuple(violations)


# frob:ticket T-0553
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov001_waiver_does_not_blanket_suppress_sibling_symbol  # noqa: E501
# frob:enforces CHK-GATE-COV002
def _cov002_check_symref(
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    symref: str,
    open_scopes: list[tuple[str, tuple[str, ...]]],
    diff: Diff,
    active_ticket: str | None = None,
) -> Violation | None:
    """The COV002 `Violation` for one touched `symref`, or None when it is
    accounted for by a direct ticket edge (open, or `DONE` within this same
    uncommitted diff -- T-0214), its `.strata` module's edge, or an
    unambiguous open ticket's scope (B10, see `_scope_covers`)."""
    if _bound_to_open_ticket(snapshot, queue, symref, diff):
        return None
    if _covered_by_strata_module(snapshot, queue, symref, diff):
        _log.debug("COV002: %s covered by its .strata module's ticket edge", symref)
        return None
    record = snapshot.symbols[symref]
    if _scope_covers(record.id.path, open_scopes, active_ticket):
        _log.debug("COV002: %s covered by an open ticket's scope", symref)
        return None
    _log.debug("COV002: %s changed with no open ticket", symref)
    return Violation(
        rule="COV002",
        severity=Severity.ERROR,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"COV002: {symref} changed with no frob:ticket edge to an open "
            f"ticket; run: frob ticket new, then add: frob:ticket <id>"
        ),
        # T-0553 (B11): COV002 is precisely about ONE changed symbol, so
        # set `symref` for `_match_waiver`'s symbol-exact matching --
        # without it, one `frob:waive COV002` anywhere in the file
        # blanket-suppresses the missing-ticket-coverage check for every
        # other changed symbol in that file.
        symref=symref,
    )


def _cov003(queue: TicketQueue, tests: CollectedTests) -> tuple[Violation, ...]:
    """COV003: a done ticket's evidence ids do not resolve to a collected
    test -- OR, for a `cmd:` entry (T-0215), do not resolve to a
    well-formed cmd: shape on a kind-permitted (docs) ticket. See
    `_evidence_valid_for_ticket` for exactly what each evidence class
    proves and why a cmd: entry is format+kind checked here rather than
    re-executed."""
    allowed_kinds = sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS)
    violations: list[Violation] = []
    for ticket in queue.tickets.values():
        if ticket.state != TicketState.DONE:
            continue
        violations.extend(
            _cov003_evidence_violation(ticket, evidence, allowed_kinds, tests)
            for evidence in ticket.evidence
            if not _evidence_valid_for_ticket(evidence, ticket, tests)
        )
    return tuple(violations)


# frob:ticket T-1161
def _python_collection_failed_violation(detail: str) -> Violation:
    """T-1161: the ONE `COV003` `Violation` `coverage_gate` reports in
    place of `_cov003`'s normal per-evidence sweep when `collect_python_
    tests` itself failed outright (the 2026-07-28 incident: a corrupted
    `.venv/bin/pytest` shim broke `uv run pytest` entirely, and every one
    of 6219 archived evidence ids independently "failed to resolve" with
    no hint the real, single cause was a broken collector, not 6219 bad
    evidence ids). `detail` is `frob.testing.python_collection_failure_
    detail()`'s captured argv/exit-code/stderr-tail text."""
    return Violation(
        rule="COV003",
        severity=Severity.ERROR,
        file="pytest --collect-only",
        line=0,
        message=(
            "COV003: pytest collection itself failed -- every Python "
            "evidence id is unresolved as a consequence of this ONE root "
            f"cause, not independently broken; run `frob doctor` (T-1161's "
            "venv-shim shebang scan may name the fix) and re-run `uv run "
            f"pytest --collect-only` by hand to confirm. {detail}"
        ),
    )


def _missing_native_remedy(tests: CollectedTests) -> str:
    """A remedy clause naming every declared-but-unbuilt native extension and
    its build command (T-0333), or `''` if all declared natives are built.
    An unbuilt native `importorskip`-skips its tests, so bound evidence on
    those tests cannot resolve -- the real fix is to build the native, NOT to
    touch the evidence id."""
    if not tests.missing_natives:
        return ""
    parts = ", ".join(
        f"{spec.name} (run: {spec.build_cmd})" for spec in tests.missing_natives
    )
    return (
        f"; a declared native extension is not built, which skips its tests: "
        f"{parts} -- build it, then re-run"
    )


# frob:enforces CHK-GATE-COV003
def _cov003_evidence_violation(
    ticket, evidence: str, allowed_kinds: list[str], tests: CollectedTests
) -> Violation:  # noqa: ANN001
    """The COV003 `Violation` for one of `ticket`'s evidence ids that
    already failed `_evidence_valid_for_ticket` -- a cmd: entry on a
    kind-disallowed ticket, or a pytest node id that never collected. When a
    declared native extension is unbuilt (T-0333), the remedy names it and
    its build command rather than blaming the evidence id."""
    _log.debug("COV003: %s evidence %s not collected", ticket.id, evidence)
    if is_cmd_evidence(evidence):
        message = (
            f"COV003: {ticket.id} evidence {evidence!r} is cmd: evidence "
            f"but kind={ticket.kind.value!r} is not in "
            f"{allowed_kinds}; fix the ticket's kind or replace with "
            f"pytest --evidence node ids"
        )
    else:
        native_remedy = _missing_native_remedy(tests)
        # frob:ticket T-0292
        # The collection cache is content-hash keyed and self-refreshes; do
        # NOT name a `frob test --collect` flag (it does not exist, T-0292).
        remedy = native_remedy or (
            "; the collection cache is keyed on test file content and "
            "refreshes automatically on the next `frob test` / `frob check` "
            "run -- if it still does not resolve, delete "
            ".frob/pytest-collect.json (or .frob/cargo-collect.json for rust) "
            "to force a rebuild, or fix the evidence id"
        )
        message = (
            f"COV003: {ticket.id} evidence {evidence!r} does not resolve "
            f"to a collected test{remedy}"
        )
    return Violation(
        rule="COV003",
        severity=Severity.ERROR,
        file=f"tickets/{ticket.id}",
        line=0,
        message=message,
    )


def _cov004(queue: TicketQueue) -> tuple[Violation, ...]:
    """COV004: attachment sha256 mismatch or missing file (root taken from ticket path
    conventions -- `tickets/` is `frob.tickets`' fixed, undocumented-as-API layout,
    documented duplicate of `frob.tickets._store.tickets_dir`)."""
    violations: list[Violation] = []
    for ticket in queue.tickets.values():
        for attachment in ticket.attachments:
            path = Path("tickets") / attachment.path
            _log.debug("COV004: checking attachment %s", path)
            violations.extend(_cov004_one(ticket, attachment, path))
    return tuple(violations)


# frob:enforces CHK-GATE-COV004
# frob:ticket T-1455
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov004_matching_sha_is_clean
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov004_missing_attachment
def _cov004_one(
    ticket: Ticket,
    attachment,  # noqa: ANN001
    path: Path,
) -> tuple[Violation, ...]:
    """COV004 check for one attachment, resolved relative to the gate's root.

    Fires only when the attachment file is missing or its sha256 no longer
    matches the recorded digest. This function shipped as an
    unconditional-fire stub (no existence/sha check at all) and sat
    unnoticed until the first real `frob ticket attach` use on 2026-08-02
    fired it on a byte-identical file."""
    recorded = getattr(attachment, "sha256", "") or ""
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        actual = None
    if actual is not None and recorded and actual == recorded:
        return ()
    return (
        Violation(
            rule="COV004",
            severity=Severity.ERROR,
            file=str(path),
            line=0,
            message=(
                f"COV004: {ticket.id} attachment {attachment.path} sha mismatch or "
                f"missing; run: frob ticket attach {ticket.id} again"
            ),
        ),
    )


# frob:ticket T-0297
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov005_directive_rebound_to_private_symbol_flags  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov005_same_symbol_no_rebind_is_clean  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov005_no_old_blob_is_clean
def _cov005(root: Path, snapshot: GraphSnapshot, diff: Diff) -> tuple[Violation, ...]:
    """COV005: a `frob:` directive whose (kind, target) pair now binds a
    PRIVATE symbol but bound a PUBLIC symbol in the same file at `diff.base`
    -- a displaced obligation (T-0297). COV001 only checks that a directive
    attaches to SOME resolvable symbol, never whether it is still attached
    to the symbol it was written for; extracting a private helper directly
    above an existing public `def` silently rebinds that def's trailing
    `frob:` directives onto the new helper (`_enclosing`/`following`
    resolution binds to the nearest symbol, not the author's intent), and
    every other gate stays green because the directive still resolves. This
    bit twice in this repo's own history (`scan_tree`, `renumber_one`) and
    was only caught by manual review.

    Restricted to files this diff actually touches (git-diff-aware, per the
    ticket's candidate (a)) and to tracked files with a resolvable blob at
    `diff.base` -- a brand-new file has no "before" to compare against, so
    it is not in scope for a rebind check, only COV001 is. A `(kind,
    target)` pair alone is NOT a unique directive identity -- this
    repository's own convention reuses one `frob:doc <page>#<anchor>`
    target across every public function a doc page covers, so comparing
    old vs new bindings file-wide would flag every pre-existing private
    helper that happens to share an anchor with some unrelated public
    function elsewhere in the same file, none of which this diff touched.
    The candidate new binding is only in scope for a rebind check if the
    NEW private symbol's own span overlaps one of this diff's hunks in
    that file -- i.e. the private symbol carrying the directive is itself
    part of what this diff just changed, which is exactly the "extracted
    helper directly above an existing def" shape the ticket describes.
    """
    new_edges_by_file: dict[str, list[Edge]] = {}
    for edge in snapshot.edges:
        # edge.origin is "path:lineno" (dsl._parse_line), not a bare path --
        # the symbol's own file (edge.src's "path::qualname" prefix) is the
        # correct file key here.
        file_key = edge.src.split("::", 1)[0]
        new_edges_by_file.setdefault(file_key, []).append(edge)
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    violations: list[Violation] = []
    for file in sorted({hunk.file for hunk in diff.hunks}):
        violations.extend(
            _cov005_file(
                root,
                diff.base,
                file,
                new_edges_by_file.get(file, ()),
                hunks_by_file.get(file, []),
                snapshot,
            )
        )
    return tuple(violations)


# frob:enforces CHK-GATE-COV005
def _cov005_file(
    root: Path,
    base: str,
    file: str,
    new_edges: Sequence[Edge],
    file_hunks: list[tuple[int, int]],
    snapshot: GraphSnapshot,
) -> list[Violation]:
    """COV005 for one diff-touched `file`: every old-public-now-private
    directive rebind whose new (private) symbol overlaps `file_hunks`."""
    old_bindings = _old_directive_bindings(root, base, file)
    if not old_bindings:
        return []
    new_by_key: dict[tuple[EdgeKind, str], list[Edge]] = {}
    for edge in new_edges:
        new_by_key.setdefault((edge.kind, edge.target), []).append(edge)
    # T-0529: qualnames already privately bound to a given (kind, target) at
    # `base` -- a new private edge for one of THESE qualnames is the same
    # binding continuing, never a rebind, even when some OTHER symbol also
    # shares the anchor and was public (see `_old_directive_bindings`).
    already_private: dict[tuple[EdgeKind, str], set[str]] = {}
    for kind, target, qualname, was_public in old_bindings:
        if not was_public:
            already_private.setdefault((kind, target), set()).add(qualname)
    violations: list[Violation] = []
    for kind, target, _qualname, was_public in old_bindings:
        if not was_public:
            continue
        for new_edge in new_by_key.get((kind, target), ()):
            record = snapshot.symbols.get(new_edge.src)
            if record is None or record.public:
                continue
            new_qualname = (
                new_edge.src.split("::", 1)[1] if "::" in new_edge.src else new_edge.src
            )
            if new_qualname in already_private.get((kind, target), ()):
                continue
            if not any(_overlaps(span, record.span) for span in file_hunks):
                continue
            _log.debug(
                "COV005: %s:%s %s rebound onto private %s (was public at %s)",
                kind.value,
                target,
                file,
                new_edge.src,
                base,
            )
            violations.append(
                Violation(
                    rule="COV005",
                    severity=Severity.ERROR,
                    file=file,
                    line=record.span[0],
                    message=(
                        f"COV005: frob:{kind.value} {target} now binds "
                        f"{new_edge.src} (private), but the same "
                        f"directive bound a PUBLIC symbol in this file "
                        f"before this change -- looks like it silently "
                        f"rode along onto an extracted/renamed helper; "
                        f"move the directive back onto the intended "
                        f"public symbol"
                    ),
                )
            )
    return violations


# frob:waive ARCH103 reason="T-0977: `git show`-and-parse helper -- reads the base \
# revision's blob, parses its frob: directives, degrades to empty on any \
# not-found/parse failure; the parse-degrade branching IS the single 'old directive \
# bindings, or none' concern the docstring names"
def _old_directive_bindings(
    root: Path, base: str, file: str
) -> tuple[tuple[EdgeKind, str, str, bool], ...]:
    """`(kind, target, qualname, was_public)` for every `frob:` directive
    `file` carried at revision `base`, parsed from `git show <base>:<file>`
    -- empty (not an error) if the blob does not exist there (new file) or
    fails to parse. `qualname` is kept (T-0529 fix) so `_cov005_file` can
    tell "this exact symbol was already privately bound to this anchor
    before" apart from "some OTHER symbol shares this anchor and happens
    to be public" -- a shared doc anchor legitimately covering BOTH a
    public entrypoint and one of its private helpers (this repo's own
    convention, e.g. kernel.md#capacity-semantics naming
    `FactBase.propagated_demand` alongside `_flow_fanout`) is not a
    "silent rebind," and conflating them by dropping symbol identity was a
    real false positive (any edit inside the private helper's own
    unrelated span used to trip COV005 purely because the SAME anchor
    string was, elsewhere, also historically public).

    A throwaway same-suffix temp file is used so `frob.lang.parse_file`'s
    extension dispatch sees the right grammar; the temp path itself never
    leaks into the returned bindings (only `kind`/`target`/`qualname`/
    publicness do),
    so it need not match `file`'s real repo-relative path.
    """
    import tempfile

    from frob.graph.dsl import parse_directives
    from frob.lang import parse_file  # local import: keep gates' top import list lean

    shown = run_argv(("git", "-C", str(root), "show", f"{base}:{file}"))
    if shown.is_err or shown.danger_ok.returncode != 0:
        return ()
    suffix = Path(file).suffix
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=suffix, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(shown.danger_ok.stdout)
            tmp_path = Path(tmp.name)
        parsed_result = parse_file(tmp_path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    if parsed_result.is_err:
        _log.debug(
            "COV005: could not parse old blob %s:%s (%s); skipping",
            base,
            file,
            parsed_result.danger_err,
        )
        return ()
    parsed = parsed_result.danger_ok
    edges, _malformed = parse_directives(parsed)
    public_by_qualname = {s.qualname: s.public for s in parsed.symbols}
    bindings: list[tuple[EdgeKind, str, str, bool]] = []
    for edge in edges:
        qualname = edge.src.split("::", 1)[1] if "::" in edge.src else edge.src
        was_public = public_by_qualname.get(qualname, False)
        bindings.append((edge.kind, edge.target, qualname, was_public))
    return tuple(bindings)


_PY_IMPORT_AS_RE = re.compile(r"\b([\w.]+)\s+as\s+(\w+)\b")
_PY_FROM_IMPORT_BLOCK_RE = re.compile(
    r"from\s+[\w.]+\s+import\s*\(([^)]*)\)", re.DOTALL
)
_PY_FROM_IMPORT_LINE_RE = re.compile(r"from\s+[\w.]+\s+import\s+([^\n(]+)")
_PY_IMPORT_LINE_RE = re.compile(r"^\s*import\s+[\w.]+\s+as\s+\w+", re.MULTILINE)


def _py_import_aliases(source: str) -> dict[str, str]:
    """`local alias name -> real short name` for Python `X as Y` imports in
    `source` (single-line `from ... import a as b`, parenthesized
    multi-line `from ... import (\\n    a as b,\\n)`, and `import a as b`),
    best-effort regex scan -- no AST, so a same-spelled non-import `as`
    (e.g. `with ctx() as x`) could in principle be swept in, but import
    aliasing is what T-0516's `_cov006_public_wrapper_reachable` needs to
    see through: a test importing a public wrapper under a local alias
    (routinely done to dodge pytest collecting a `test_*`-named import as
    its own test item) calls the ALIAS by name, never the wrapper's real
    short name, which otherwise defeats this rescue's name-based match.
    Python only -- other grammars' import-aliasing syntax differs enough
    that this scan does not attempt to cover them (T-0516 Done report).
    """
    aliases: dict[str, str] = {}
    for block in _PY_FROM_IMPORT_BLOCK_RE.findall(source):
        for real, alias in _PY_IMPORT_AS_RE.findall(block):
            aliases[alias] = real.rsplit(".", 1)[-1]
    for line in _PY_FROM_IMPORT_LINE_RE.findall(source):
        for real, alias in _PY_IMPORT_AS_RE.findall(line):
            aliases[alias] = real.rsplit(".", 1)[-1]
    for line in source.splitlines():
        if _PY_IMPORT_LINE_RE.match(line):
            for real, alias in _PY_IMPORT_AS_RE.findall(line):
                aliases[alias] = real.rsplit(".", 1)[-1]
    return aliases


_PROTOCOL_DUNDER_NAMES = frozenset(
    {
        "__enter__",
        "__exit__",
        "__getattr__",
        "__setattr__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
        "__iter__",
        "__next__",
        "__call__",
        "__len__",
        "__contains__",
    }
)
_COV006_VALIDATOR_DECORATORS = frozenset({"field_validator", "model_validator"})
_DECORATOR_LINE_RE = re.compile(r"^\s*@(\w+)")
_PY_FROM_IMPORT_PAREN_MODULE_RE = re.compile(
    r"from\s+([\w.]+)\s+import\s*\(([^)]*)\)", re.DOTALL
)
_PY_FROM_IMPORT_LINE_MODULE_RE = re.compile(
    r"^[ \t]*from\s+([\w.]+)\s+import\s+([^(\n]+)$", re.MULTILINE
)


# frob:ticket T-0528
def _cov006_decorator_names(source_lines: list[str], start_line: int) -> list[str]:
    """Decorator names spanning 1-indexed `start_line` downward (a symbol's
    span start is the FIRST decorator line, not the `def` line -- `frob.lang`
    includes leading decorators in a symbol's span), stopping at the first
    non-decorator line (the `def`/`class` line itself). Used by
    `_cov006_implicit_dispatch_reachable` (T-0528, Class 1) to recognize a
    pydantic `@field_validator`/`@model_validator` method: that method is
    invoked by the FRAMEWORK during model construction, never by a literal
    `name(...)` call anywhere in source, so the call-graph token scanner
    can never see it by construction.
    """
    names: list[str] = []
    i = start_line - 1
    while i < len(source_lines):
        line = source_lines[i]
        match = _DECORATOR_LINE_RE.match(line)
        if match is None:
            break
        names.append(match.group(1))
        i += 1
    return names


# frob:ticket T-0528
# frob:waive ARCH001 reason="a multi-stage heuristic (dunder-check, then validator-decorator check, then receiver derivation, then an optional graph-closure fallback) where each stage's guard depends on locals the prior stage bound (target_sym, is_dunder/is_validator, receiver); splitting stages into helpers would thread 4-5 locals across new boundaries, adding indirection without reducing the sequential logic itself"  # noqa: E501
def _cov006_implicit_dispatch_reachable(root: Path, edge: Edge) -> bool:
    """COV006 rescue for Class 1's dunder/validator shapes (T-0528): a
    private target invoked IMPLICITLY by the Python runtime (a protocol
    dunder like `__exit__`/`__getattr__`, triggered by `with`/attribute-
    access syntax) or by a decorator-driven framework (a pydantic
    `@field_validator`/`@model_validator` method, triggered by model
    construction) -- neither shape is ever a literal `name(` call token
    anywhere in source, which is the only thing `_called_names` can see by
    construction. Accepts reachability when the target is one of these
    implicit-dispatch shapes AND its owning receiver (the dunder's class,
    the validator's model class, or -- for a bare module-level dunder like
    `__getattr__` -- the module itself) is referenced anywhere in the
    test's own source text. Looser than a call-graph proof (it cannot
    confirm the specific method fired, only that its receiver is in play)
    -- acceptable for a WARN-tier, best-effort rescue, matching this gate's
    existing calibration tier.

    Also covers one further indirection: the bound target may not be the
    validator method itself but a plain helper the validator calls
    directly (e.g. `Ticket`'s `_normalize_scope` field_validator calling
    `_split_scope_entries`) -- the FRAMEWORK invokes the validator
    implicitly, but the validator then calls the helper with an ordinary,
    call-graph-visible `name(` token. Accepted when some same-file
    validator method's private-call closure reaches the target.
    """
    from frob.lang import parse_file

    target_file = edge.target.split("::", 1)[0]
    if not target_file.endswith(".py"):
        return False
    target_qualname = edge.target.split("::", 1)[1]
    short = target_qualname.rsplit(".", 1)[-1]

    target_parsed = parse_file(root / target_file)
    if target_parsed.is_err:
        return False
    target_sym = next(
        (
            sym
            for sym in target_parsed.danger_ok.symbols
            if sym.qualname == target_qualname
        ),
        None,
    )
    if target_sym is None:
        return False

    is_dunder = short in _PROTOCOL_DUNDER_NAMES
    is_validator = False
    source_lines = (root / target_file).read_text(encoding="utf-8").splitlines()
    if not is_dunder:
        decorators = _cov006_decorator_names(source_lines, target_sym.span[0])
        is_validator = any(d in _COV006_VALIDATOR_DECORATORS for d in decorators)

    if "." in target_qualname:
        receiver = target_qualname.split(".", 1)[0]
    else:
        # A bare module-level dunder (e.g. a lazy `__getattr__`): the
        # receiver is the module itself, referenced by its filename stem.
        receiver = target_file.rsplit("/", 1)[-1].removesuffix(".py")

    if not is_dunder and not is_validator:
        # T-0528: the bound target may not be the validator ITSELF, but a
        # plain helper the validator calls directly (e.g. `Ticket`'s
        # `_normalize_scope` field_validator calling `_split_scope_entries`)
        # -- the framework invokes the validator implicitly, the validator
        # then calls the helper by a literal name the call graph CAN see.
        # Accept when some same-file validator method reaches the target
        # (directly, or through any depth of private-helper indirection)
        # and that validator's own class is referenced in the test.
        from frob.graph.callgraph import build_call_graph, closure

        target_symref = f"{target_file}::{target_qualname}"
        target_graph = build_call_graph(root, (target_file,))
        validator_found = False
        for sym in target_parsed.danger_ok.symbols:
            sym_decorators = _cov006_decorator_names(source_lines, sym.span[0])
            if not any(d in _COV006_VALIDATOR_DECORATORS for d in sym_decorators):
                continue
            wrapper_symref = f"{target_file}::{sym.qualname}"
            if wrapper_symref == target_symref:
                continue
            if target_symref in closure(
                target_graph, wrapper_symref, max_depth=8, max_nodes=200
            ):
                validator_found = True
                receiver = sym.qualname.split(".", 1)[0]
                break
        if not validator_found:
            return False

    test_file = edge.src.split("::", 1)[0]
    if not (root / test_file).is_file():
        return False
    test_source = (root / test_file).read_text(encoding="utf-8")
    return receiver in test_source


def _cov006_module_path_to_file(root: Path, module_path: str) -> str | None:
    """Best-effort dotted python module path -> repo-root-relative source
    file, trying both a direct module file and a package `__init__.py`
    (T-0528). Returns `None` when neither exists under this repo's `src/`
    layout (pyproject's `packages = { find = { where = ["src"] } }`).
    """
    rel = module_path.replace(".", "/")
    for candidate in (f"src/{rel}.py", f"src/{rel}/__init__.py"):
        if (root / candidate).is_file():
            return candidate
    return None


def _cov006_imported_names(source: str) -> list[tuple[str, list[str]]]:
    """`(dotted module path, [imported names])` pairs for every python
    `from ... import ...` statement in `source`, both single-line and
    parenthesized multi-line -- feeds `_cov006_resolve_import_files`
    (T-0528, Class 2). Best-effort regex scan, python only, same spirit as
    `_py_import_aliases`.
    """
    results: list[tuple[str, list[str]]] = []
    for module_path, blob in _PY_FROM_IMPORT_PAREN_MODULE_RE.findall(source):
        names = [n.split(" as ")[0].strip() for n in blob.split(",")]
        results.append((module_path, [n for n in names if n.isidentifier()]))
    for module_path, blob in _PY_FROM_IMPORT_LINE_MODULE_RE.findall(source):
        names = [n.split(" as ")[0].strip() for n in blob.split(",")]
        results.append((module_path, [n for n in names if n.isidentifier()]))
    return results


def _cov006_resolve_import_files(
    root: Path, source: str, names_of_interest: frozenset[str]
) -> set[str]:
    """Repo-root-relative source files that `source`'s own `from ... import
    ...` statements plausibly resolve to, for whichever imported names are
    in `names_of_interest` (T-0528, Class 2): each `from a.b.c import name`
    resolves the dotted module path to a candidate file; if that file does
    not itself DEFINE the imported name (only re-exports it via its own
    `from a.b.c.d import name` line -- the common package `__init__.py`
    re-export shape), the same resolution repeats once more against THAT
    file to reach the real defining module. Two hops deep, matching every
    shape measured in T-0528's Class 2 audit (a public entrypoint
    re-exported exactly once through a package `__init__.py`); best-effort
    and python-only, feeds `_cov006_third_file_reachable`.
    """
    files: set[str] = set()
    for module_path, names in _cov006_imported_names(source):
        for name in names:
            if name not in names_of_interest:
                continue
            candidate = _cov006_module_path_to_file(root, module_path)
            if candidate is None:
                continue
            resolved = _cov006_chase_reexport_hops(root, candidate, name)
            if resolved is not None:
                files.add(resolved)
    return files


def _cov006_chase_reexport_hops(root: Path, candidate: str, name: str) -> str | None:
    """Follow `candidate`'s own re-export chain up to two hops to find the
    file that actually DEFINES `name`, or the last file reached if neither
    hop resolves further (extracted from `_cov006_resolve_import_files` to
    cut nesting, T-0394; see that function's docstring for the two-hop
    re-export shape this chases). Each imported NAME is chased
    independently (not the whole `from ... import a, b` group at once): a
    package `__init__.py` routinely re-exports several names from
    DIFFERENT submodules in separate lines, so grouping would let one
    name's resolved hop silently steal the search for another (T-0528 fix
    during calibration -- the first version of this helper had exactly
    that bug)."""
    from frob.lang import parse_file

    for _hop in range(2):
        parsed = parse_file(root / candidate)
        if parsed.is_err:
            return None
        defined = {sym.qualname for sym in parsed.danger_ok.symbols}
        if name in defined:
            return candidate
        reexport_source = (root / candidate).read_text(encoding="utf-8")
        next_candidate = None
        for mod2, names2 in _cov006_imported_names(reexport_source):
            if name in names2:
                next_candidate = _cov006_module_path_to_file(root, mod2)
                break
        if next_candidate is None:
            return candidate
        candidate = next_candidate
    return None


def _cov006_expand_project_imports(
    root: Path, start_files: frozenset[str], max_depth: int = 2
) -> set[str]:
    """BFS closure of `start_files`' OWN project-internal (`frob.*`)
    imports, regardless of which names are used (T-0528, Class 2): the
    entrypoint a test calls often lives in a package `__init__.py` that
    re-exports it from a THIRD file, which in turn imports from a FOURTH
    file that actually reaches the bound private target (e.g.
    `frob.lang.__init__.parse_file` -> `frob.lang._extract.extract` ->
    `frob.lang._common._find_following_symbol`) -- one more hop than
    `_cov006_resolve_import_files`'s name-targeted two-hop re-export chase
    can see, since that helper only follows a SPECIFIC name's re-export,
    not a file's whole import list. Bounded to `max_depth` hops and to
    `frob.`-rooted modules (this repo's own package) to keep the widened
    file set small and stdlib/third-party imports out of scope.
    """
    seen = set(start_files)
    frontier = set(start_files)
    for _depth in range(max_depth):
        next_frontier: set[str] = set()
        for file_path in frontier:
            if not (root / file_path).is_file():
                continue
            source = (root / file_path).read_text(encoding="utf-8")
            for module_path, _names in _cov006_imported_names(source):
                if not module_path.startswith("frob."):
                    continue
                candidate = _cov006_module_path_to_file(root, module_path)
                if candidate is not None and candidate not in seen:
                    next_frontier.add(candidate)
        seen |= next_frontier
        frontier = next_frontier
        if not frontier:
            break
    return seen


def _cov006_full_call_graph(root: Path, paths: tuple[str, ...]):
    """Caller -> callee symref graph over `paths` recording EVERY resolved
    call, public OR private (T-0528, `_cov006_third_file_reachable` only)
    -- unlike the shared `frob.graph.callgraph.build_call_graph`, which
    deliberately drops edges into public callees so `frob.dup`/arch's
    closures stop at the public-API boundary for free (T-0483). That
    exclusion is exactly what makes a multi-file public-wrapper chain
    (test -> public entrypoint in file A -> public entrypoint in file B ->
    private target in file B) invisible even once every file involved is
    in scope: the FIRST public-to-public hop never gets an edge. This local
    variant exists only to bridge that specific gap for COV006's Class 2
    rescue; the shared substrate and its other two consumers
    (T-0288/T-0290) are untouched.
    """
    from frob.graph.callgraph import CallGraph, _called_names, _short_name
    from frob.lang import parse_file

    parsed_by_path: dict[str, list] = {}
    for path in paths:
        result = parse_file(root / path)
        if result.is_err:
            continue
        parsed_by_path[path] = list(result.danger_ok.symbols)

    by_name: dict[str, list[str]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            by_name.setdefault(_short_name(sym.qualname), []).append(
                f"{path}::{sym.qualname}"
            )

    calls: dict[str, tuple[str, ...]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            caller_symref = f"{path}::{sym.qualname}"
            called_names = _called_names(sym.body_tokens)
            callees = [
                symref
                for name in called_names
                for symref in by_name.get(name, ())
                if symref != caller_symref
            ]
            if callees:
                calls[caller_symref] = tuple(callees)
    return CallGraph(calls=calls)


# frob:ticket T-0528
# frob:ticket T-0814
def _is_symref(entry: str) -> bool:
    """True if `entry` looks like a real `path::qualname` call-graph node
    (a `closure()`/`CallGraph.calls` entry), false for a non-symref
    sentinel such as `frob.graph.callgraph.UNRESOLVED_CALLEE` -- every
    closure consumer here must check this before `split("::", 1)[1]`,
    which IndexErrors on a bare sentinel with no `::` (T-0814). Thin
    wrapper over `frob.graph.callgraph.is_symref` (extracted T-0861)."""
    from frob.graph.callgraph import is_symref

    return is_symref(entry)


def _cov006_third_file_reachable(root: Path, edge: Edge) -> bool:
    """COV006 rescue for Class 2 (T-0528): the test reaches the bound
    private target through a real call chain passing through a THIRD file
    -- neither the test's own file nor the target's file -- e.g. the test
    calls a public entrypoint re-exported from a package `__init__.py`
    (really defined in module A), which calls a private helper in the SAME
    file A, which itself calls the private target in file B. Every hop in
    that chain is a genuine private-callee call edge `build_call_graph`
    already records; `_cov006`'s direct closure check misses it only
    because it scopes `build_call_graph` to `(test_file, target_file)`, so
    file A is never parsed at all. This widens the scope to also include
    every file the test's own `called_names` plausibly resolve to via
    import (`_cov006_resolve_import_files`), then seeds `closure` at EACH
    called name that resolves to a PUBLIC entrypoint in one of those widened
    files (not at the test's own symref) -- `build_call_graph` never
    records an edge INTO a public callee (T-0483's public-boundary-stop
    behavior, load-bearing for `frob.dup`/arch and left untouched), so a
    closure seeded at the test itself could never cross that first
    test -> public-entrypoint hop either, the same reason `_cov006`'s own
    direct check misses this shape in the first place. Seeding at the
    entrypoint instead sidesteps that one hop exactly the way
    `_cov006_public_wrapper_reachable` already does for the same-file case.

    The test's own "called names" are gathered not just from the bound
    test method's own body, but transitively through any SAME-FILE PRIVATE
    helper it calls too (e.g. a shared `_load_model(...)` fixture helper
    that itself calls the real entrypoint) -- `build_call_graph` over the
    test file alone already records that private-callee edge, so its
    `closure` gives the full same-file helper set for free.

    Python test files only (import resolution is python-specific).
    """
    test_file = edge.src.split("::", 1)[0]
    target_file = edge.target.split("::", 1)[0]
    if not test_file.endswith(".py"):
        return False

    called = _cov006_test_and_helper_called_names(root, edge, test_file)
    if not called:
        return False

    test_source = (root / test_file).read_text(encoding="utf-8")
    aliases = _py_import_aliases(test_source)
    resolved_called = frozenset({aliases.get(name, name) for name in called})
    import_files = _cov006_resolve_import_files(root, test_source, resolved_called)
    if not import_files:
        return False
    expanded_files = _cov006_expand_project_imports(
        root, frozenset(import_files) | {target_file}
    )
    candidate_files = {test_file, target_file, *import_files, *expanded_files}
    if len(candidate_files) <= 2:
        return False
    ordered_files = tuple(sorted(candidate_files))
    graph = _cov006_full_call_graph(root, ordered_files)

    entrypoints = _cov006_third_file_entrypoints(root, import_files, resolved_called)
    if not entrypoints:
        return False
    from frob.graph.callgraph import closure

    return any(
        edge.target in closure(graph, entrypoint, max_depth=8, max_nodes=200)
        for entrypoint in entrypoints
    )


# frob:ticket T-0976
def _cov006_test_and_helper_called_names(
    root: Path, edge: Edge, test_file: str
) -> set[str]:
    """The bound test's own called-name set, transitively expanded through
    every SAME-FILE PRIVATE helper it calls (`build_call_graph` over the
    test file alone already records that private-callee edge) -- the
    called-names-gathering half of `_cov006_third_file_reachable`, split
    from the import-resolution/entrypoint-search half. Empty set if the
    test symbol cannot be located."""
    from frob.graph.callgraph import _called_names, build_call_graph, closure
    from frob.lang import parse_file

    test_parsed = parse_file(root / test_file)
    if test_parsed.is_err:
        return set()
    test_qualname = edge.src.split("::", 1)[1]
    test_symbols = test_parsed.danger_ok.symbols
    test_sym = next(
        (sym for sym in test_symbols if sym.qualname == test_qualname), None
    )
    if test_sym is None:
        return set()
    called = set(_called_names(test_sym.body_tokens))
    test_only_graph = build_call_graph(root, (test_file,))
    reached_helpers = closure(test_only_graph, edge.src, max_depth=6, max_nodes=100)
    symbols_by_qualname = {sym.qualname: sym for sym in test_symbols}
    for helper_symref in reached_helpers:
        if not _is_symref(helper_symref):
            # T-0814: a non-symref sentinel (e.g. UNRESOLVED_CALLEE) has no
            # `::` to split on -- skip it, it names no real helper symbol.
            continue
        helper_qualname = helper_symref.split("::", 1)[1]
        helper_sym = symbols_by_qualname.get(helper_qualname)
        if helper_sym is not None:
            called |= _called_names(helper_sym.body_tokens)
    return called


# frob:ticket T-0976
def _cov006_third_file_entrypoints(
    root: Path, import_files: set[str], resolved_called: frozenset[str]
) -> set[str]:
    """Every public symbol, in one of `import_files`, whose short name is
    in `resolved_called` -- the candidate entrypoints
    `_cov006_third_file_reachable` seeds its closure search at, since
    `build_call_graph` never records an edge INTO a public callee
    (T-0483)."""
    from frob.lang import parse_file

    entrypoints: set[str] = set()
    for third_file in import_files:
        parsed = parse_file(root / third_file)
        if parsed.is_err:
            continue
        for sym in parsed.danger_ok.symbols:
            short = sym.qualname.rsplit(".", 1)[-1]
            if sym.public and short in resolved_called:
                entrypoints.add(f"{third_file}::{sym.qualname}")
    return entrypoints


def _cov006_dispatcher_holds_bare_target(
    dispatcher: RawSymbol, target_short_name: str
) -> bool:
    """True if `dispatcher`'s own body tokens reference `target_short_name`
    as a bare, non-call token (never `name(`) -- the T-0528 Class 1
    dispatch-table literal shape (extracted from
    `_cov006_dispatch_table_wrapper_names` to cut nesting, T-0394)."""
    tokens = dispatcher.body_tokens
    for i, tok in enumerate(tokens):
        if tok != target_short_name:
            continue
        if i + 1 < len(tokens) and tokens[i + 1] == "(":
            continue
        return True
    return False


def _cov006_dispatch_table_wrapper_names(
    target_file: str,
    target_symbols: tuple[RawSymbol, ...],
    target_graph: "CallGraph",
    target_qualname: str,
) -> set[str]:
    """T-0528 Class 1 last-resort widening (extracted from
    `_cov006_public_wrapper_reachable` to cut nesting, T-0394): if no
    wrapper reaches the target via real calls, accept a private function
    that holds the target's short name as a bare dispatch-table token, as
    long as that dispatch-holding function is itself call-reachable from a
    public wrapper. See `_cov006_public_wrapper_reachable`'s own docstring
    for the full rationale."""
    from frob.graph.callgraph import _short_name, closure

    target_short_name = _short_name(target_qualname)
    for sym in target_symbols:
        if not sym.public:
            continue
        wrapper_symref = f"{target_file}::{sym.qualname}"
        reached = closure(target_graph, wrapper_symref, max_depth=8, max_nodes=200)
        reached_symrefs = set(reached) | {wrapper_symref}
        for dispatcher in target_symbols:
            dispatcher_symref = f"{target_file}::{dispatcher.qualname}"
            if dispatcher_symref not in reached_symrefs:
                continue
            if _cov006_dispatcher_holds_bare_target(dispatcher, target_short_name):
                return {_short_name(sym.qualname)}
    return set()


# frob:ticket T-0506
# frob:ticket T-0516
# frob:ticket T-0528
# frob:waive ARCH001 reason="a multi-stage same-file-wrapper heuristic (resolve the target's own file, find every public symbol in it, check each calls the target, then check the test's own body calls that public symbol by name or import alias) with each stage feeding the next's candidate set; splitting would thread that same candidate-narrowing chain across new boundaries without reducing it"  # noqa: E501
def _cov006_public_wrapper_reachable(root: Path, edge: Edge) -> bool:
    """COV006 rescue: True if a PUBLIC symbol in the bound private target's
    own file is itself called, by name (or by a Python `X as Y` import
    alias resolved back to its real name, T-0516), from the test's own
    body, and reaches the private target either directly or transitively
    through same-file private helper calls -- the same-file
    test -> public-wrapper -> (private helper)* -> private-target shape
    `build_call_graph` cannot represent (it never records edges into
    public callees, T-0483). T-0506 covered only the direct one-hop case
    (wrapper calls target by name); T-0516 generalizes this to any depth
    of private-helper indirection between the public wrapper and the
    bound private target, reusing the shared private-only call graph's
    `closure` for the transitive part -- a public wrapper calling a
    private helper IS recorded as an edge (only edges INTO public symbols
    are dropped), so `closure` seeded at the wrapper's own symref already
    walks through any number of private hops on the way to the target.
    Scoped to this gate only; the shared `CallGraph` substrate is
    untouched so `frob.dup`/arch consumers keep their public-boundary-stop
    behavior.

    T-0528 (Class 1's dispatch-table shape): if no wrapper reaches the
    target via real calls, also accept a private function that lists the
    target's short name as a BARE, non-call token (never `name(`) anywhere
    in its own body -- a dispatch-table literal like
    `(_validate_krb, ...)`, later invoked through a loop variable -- as
    long as that dispatch-holding function is itself call-reachable from a
    public wrapper. `_called_names` can only ever see `name(` tokens, so
    this reference shape is invisible to the closure built above; this is
    a last-resort widening, still scoped to the one already-parsed target
    file.
    """
    from frob.graph.callgraph import (
        _called_names,
        _short_name,
        build_call_graph,
        closure,
    )
    from frob.lang import parse_file

    target_file = edge.target.split("::", 1)[0]
    test_file = edge.src.split("::", 1)[0]
    target_qualname = edge.target.split("::", 1)[1]

    target_parsed = parse_file(root / target_file)
    if target_parsed.is_err:
        return False
    target_symbols = target_parsed.danger_ok.symbols

    target_symref = f"{target_file}::{target_qualname}"
    target_graph = build_call_graph(root, (target_file,))

    # A generous, gate-local closure budget (well above `closure`'s shared
    # defaults sized for cross-package fan-out): a single wrapper in a
    # gates-style module routinely has a dozen-plus direct private
    # callees (e.g. `coverage_gate` dispatching to `_cov001".."_cov007`),
    # which exhausts the default max_nodes before ever reaching a second
    # hop. This lookup is scoped to one already-parsed file and one
    # wrapper at a time, so a larger budget here is cheap and does not
    # touch the shared `closure` defaults other consumers rely on.
    wrapper_short_names = {
        _short_name(sym.qualname)
        for sym in target_symbols
        if sym.public
        and target_symref
        in closure(
            target_graph,
            f"{target_file}::{sym.qualname}",
            max_depth=8,
            max_nodes=200,
        )
    }
    if not wrapper_short_names:
        wrapper_short_names = _cov006_dispatch_table_wrapper_names(
            target_file, target_symbols, target_graph, target_qualname
        )
    if not wrapper_short_names:
        return False

    if test_file == target_file:
        test_symbols = target_symbols
    else:
        test_parsed = parse_file(root / test_file)
        if test_parsed.is_err:
            return False
        test_symbols = test_parsed.danger_ok.symbols

    test_qualname = edge.src.split("::", 1)[1]
    test_sym = next(
        (sym for sym in test_symbols if sym.qualname == test_qualname), None
    )
    if test_sym is None:
        return False
    called = _called_names(test_sym.body_tokens)
    if wrapper_short_names & called:
        return True
    if not test_file.endswith(".py"):
        return False
    aliases = _py_import_aliases((root / test_file).read_text(encoding="utf-8"))
    resolved = {aliases.get(name, name) for name in called}
    return bool(wrapper_short_names & resolved)


# frob:ticket T-0483
# frob:enforces CHK-GATE-COV006
def _cov006(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """COV006: a `frob:tests` edge bound to a PRIVATE symbol whose named
    test has no call-graph reachability to that symbol.

    Reuses `frob.graph.callgraph` (T-0288/T-0290's shared substrate) rather
    than a second traversal implementation -- `build_call_graph` scoped to
    just the test's own file plus the bound symbol's file (the cheapest
    scope that can possibly show a direct or one-hop-private-helper path
    between them), then `closure` from the test's own symref.

    Restricted to PRIVATE targets ONLY: `build_call_graph` never records an
    edge to a PUBLIC callee by construction (its docstring: this is what
    lets dup/perf's closures stop at the public-API boundary for free), so
    a target that resolves to a public symbol would ALWAYS show up
    "unreachable" here regardless of whether the test genuinely exercises
    it -- checking public targets would be unsound, not merely noisier.
    WARN severity (not error): `frob.graph.callgraph` is an explicitly
    best-effort, name-based resolver (two same-named private helpers in
    different files can alias), so a miss is a prompt to double check, not
    proof the binding is wrong.

    T-0506: the single most common shape of "false" COV006 finding
    (T-0483, disclosed at landing) was a test that reaches its bound
    private helper only INDIRECTLY, by calling a PUBLIC entry point in
    the SAME FILE as the helper that itself calls it -- `build_call_graph`
    never records an edge INTO a public callee (that behavior is
    load-bearing for its other two consumers, T-0288/T-0290, and is left
    untouched here), so the shared graph has no edge for that first hop
    and `closure` can never walk through it. Rather than special-case the
    shared substrate, this check does its own one-hop lookahead, scoped to
    THIS gate only: `_cov006_public_wrapper_reachable` re-parses just the
    target's file (and the test's file, if different) and asks whether
    any PUBLIC symbol in the target's file both (a) calls the private
    target directly and (b) is itself called, by name, from the test's
    own body. If so, the binding is accepted as reachable one hop out
    without ever recording a public-callee edge in the shared `CallGraph`.
    A COV006 finding that survives both the direct closure check and this
    one-hop public-wrapper check is a prompt to double check, same as any
    other WARN-tier gate here on first adoption.

    `build_call_graph` re-`frob.lang.parse_file`s every path it's given, and
    a repo's own test suite routinely binds many private helpers from the
    SAME (test_file, target_file) pair -- one call graph per `frob:tests`
    edge would reparse both files once per binding. `graph_cache` memoizes
    by the exact `paths` tuple passed to `build_call_graph`, so a pair seen
    twice only builds once.

    T-0528's calibration pass added three more blindness-class rescues,
    tried in this order after the direct closure and public-wrapper checks
    above still miss:

    - `attrs.get("kind")` in `{"integration", "e2e"}` (Class 3): the
      `frob:tests` directive's own `kind=` attr (already part of the DSL,
      `frob.graph.dsl._TESTS_KINDS`) says the test drives a CLI/subprocess
      boundary a static call-graph structurally cannot represent (argparse
      dispatch-table or subprocess invocation, never a literal call);
      trusted at face value rather than re-derived here.
    - a non-python target file (Class 4): `build_call_graph`'s privacy
      resolution (`_short_name(qualname).startswith("_")`) is a PYTHON
      naming convention; Rust's `fn` (private-by-default unless `pub`) has
      no such convention, so every non-python callee looks "public" to it
      and is silently never recorded as a private edge, regardless of the
      test/target's actual reachability. Checking non-python targets here
      would be unsound noise, not signal, until `build_call_graph` gains
      real per-language privacy resolution (filed as a follow-up; see this
      ticket's Done report).
    - `_cov006_implicit_dispatch_reachable` (Class 1) and
      `_cov006_third_file_reachable` (Class 2), each documented at their
      own definition.
    """
    graph_cache: dict[tuple[str, ...], CallGraph] = {}
    violations: list[Violation] = []
    for edge in snapshot.edges:
        violation = _cov006_edge_violation(root, snapshot, edge, graph_cache)
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:ticket T-0598
def _cov006_edge_violation(
    root: Path,
    snapshot: GraphSnapshot,
    edge: Edge,
    graph_cache: dict[tuple[str, ...], CallGraph],
) -> Violation | None:
    """One `frob:tests` edge's COV006 finding, or `None` if it is out of
    scope (not a TESTS edge, public target, non-python target, an
    integration/e2e-kind edge) or reachable by the direct closure check or
    any of the three T-0528 rescue heuristics (`_cov006`'s per-edge body,
    split out for ARCH001 -- T-0598)."""
    from frob.graph.callgraph import build_call_graph, closure

    if edge.kind != EdgeKind.TESTS:
        return None
    target_record = snapshot.symbols.get(edge.target)
    if target_record is None or target_record.public:
        return None
    target_file = edge.target.split("::", 1)[0]
    if edge.attrs.get("kind") in ("integration", "e2e"):
        return None
    if not target_file.endswith(".py"):
        return None
    test_file = edge.src.split("::", 1)[0]
    paths = (test_file,) if test_file == target_file else (test_file, target_file)
    graph = graph_cache.get(paths)
    if graph is None:
        graph = build_call_graph(root, paths)
        graph_cache[paths] = graph
    if edge.target in closure(graph, edge.src):
        return None
    if _cov006_public_wrapper_reachable(root, edge):
        return None
    if _cov006_implicit_dispatch_reachable(root, edge):
        return None
    if _cov006_third_file_reachable(root, edge):
        return None
    _log.debug("COV006: %s -> %s has no call-graph reachability", edge.src, edge.target)
    return Violation(
        rule="COV006",
        severity=Severity.WARN,
        file=test_file,
        line=0,
        message=(
            f"COV006: frob:tests {edge.src} -> {edge.target} has no "
            f"call-graph reachability to the bound private symbol "
            f"(frob.graph.callgraph, best-effort); confirm the test "
            f"actually exercises it, or bind a symbol it calls"
        ),
        # T-0525: symbol-exact, not file-scoped -- a COV006 finding is
        # precisely about ONE frob:tests edge (edge.src, the test's own
        # symref). Without this, `_match_waiver` falls back to file-scope
        # matching (its symref-is-None branch) and a single `frob:waive
        # COV006` comment anywhere in `test_file` silently suppresses
        # EVERY COV006 finding in that file, including unrelated, unsound
        # ones (verified: one waiver near one test suppressed all 7
        # then-present COV006 findings in tests/test_gates.py). Mirrors
        # TEST005's T-0148 precedent (see `Violation.symref`'s docstring).
        symref=edge.src,
    )


# frob:ticket T-0483
# frob:enforces CHK-GATE-COV007
def _cov007(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """COV007: a `frob:doc` edge whose src symbol is PRIVATE.

    `frob:doc` obligations (COV001) exist to keep public-surface docs in
    sync; a private helper carrying its own doc anchor is usually either a
    directive that rode along onto the wrong symbol (see COV005's rebind
    case) or documentation that belongs on the public caller instead. WARN
    severity: a private helper can legitimately warrant its own doc anchor
    (a complex internal algorithm, say) -- this flags it for a human
    decision, it does not forbid the pattern.
    """
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.DOC:
            continue
        record = snapshot.symbols.get(edge.src)
        if record is None or record.public:
            continue
        file = edge.src.split("::", 1)[0]
        _log.debug("COV007: frob:doc on private symbol %s", edge.src)
        violations.append(
            Violation(
                rule="COV007",
                severity=Severity.WARN,
                file=file,
                line=record.span[0],
                message=(
                    f"COV007: frob:doc on private symbol {edge.src} -- doc "
                    f"anchors normally cover the public API surface; move it "
                    f"onto the public caller, or confirm this private helper "
                    f"genuinely needs its own doc anchor"
                ),
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Scope digest, scope, and pre-work gates
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0355
# frob:tests tests/test_prework_parity.py::TestScopeDigestParity.test_digest_is_content_only_portable_across_checkouts  # noqa: E501
def scope_digest(scope: Sequence[str], snapshot: GraphSnapshot) -> str:
    """Sha256 over the sorted `(file, hash)` pairs of files matching `scope`.

    THE one implementation: `frob ticket start/sweep` records it and
    `prework_gate` compares against it -- a second copy of this hash is how
    PRE001 becomes permanently stale (it happened; see tests/test_prework_parity.py).

    T-0355 (item 3): the per-file `hash` half of the pair comes from
    `frob.graph._content_hash` -- a plain sha256 of the file's bytes, never
    folded with `_stat_key`'s mtime/size (that pair is only a cheap
    invalidation check, not part of the recorded hash). Combined with the
    repo-relative path this is keyed on, a recorded sweep's digest is
    already checkout-portable: two checkouts with byte-identical scope
    files at the same relative paths produce the same digest regardless of
    absolute root, mtime, or timestamps. See
    test_digest_is_content_only_portable_across_checkouts for the pinned
    contract.
    """

    matched = sorted(
        (path, digest)
        for path, digest in snapshot.file_hashes.items()
        if scope_matches(path, scope)
    )
    hasher = hashlib.sha256()
    for path, digest in matched:
        hasher.update(f"{path}:{digest}\n".encode())
    return hasher.hexdigest()


def _scope_digest(ticket: Ticket, snapshot: GraphSnapshot) -> str:
    """`scope_digest` over a ticket's declared scope."""
    return scope_digest(ticket.scope, snapshot)


_TICKET_REF_RE = re.compile(r"T-\d{4}")

# git blame --porcelain's sentinel sha for lines not yet committed (T-0108: a
# hunk owning only this sha is real, in-progress work -- never exempt from SCOPE001).
_UNCOMMITTED_SHA = "0" * 40
_BLAME_SHA_LINE_RE = re.compile(r"^[0-9a-f]{40} ")


def _blame_shas(root: Path, file: str, start: int, end: int) -> Option[frozenset[str]]:
    """Distinct commit shas covering lines `[start, end]` of `file` at HEAD
    (`git blame --porcelain`), or `Nothing()` if blame fails (missing file,
    not a repo, etc). `_UNCOMMITTED_SHA` marks working-tree-dirty lines. Spawns
    through `frob.gitio.run_argv` -- the package's one process-with-timeout
    seam -- rather than adding a second git subprocess helper (T-0108)."""
    argv = (
        "git",
        "-C",
        str(root),
        "blame",
        "-L",
        f"{start},{end}",
        "--porcelain",
        "--",
        file,
    )
    spawned = run_argv(argv)
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.debug("scope_gate: git blame failed for %s:%d-%d", file, start, end)
        return Nothing()
    shas = frozenset(
        line.split(" ", 1)[0]
        for line in spawned.danger_ok.stdout.splitlines()
        if _BLAME_SHA_LINE_RE.match(line)
    )
    return Some(shas)


def _commit_subject(root: Path, sha: str) -> Option[str]:
    """The subject line (`%s`) of commit `sha`, or `Nothing()` if unreadable --
    read to recover the ticket id a prior commit belongs to for SCOPE001's
    cross-ticket exemption (T-0108)."""
    spawned = run_argv(("git", "-C", str(root), "log", "-1", "--format=%s", sha))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.debug("scope_gate: could not read subject of %s", sha)
        return Nothing()
    return Some(spawned.danger_ok.stdout.strip())


def _commit_parents(root: Path, sha: str) -> tuple[str, ...]:
    """Parent shas of commit `sha` (`git log -1 --format=%P`), empty if `sha`
    is a root commit or is unreadable (T-0527: used to detect a merge commit
    and recover the ticket reference its OWN subject may lack)."""
    spawned = run_argv(("git", "-C", str(root), "log", "-1", "--format=%P", sha))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.debug("scope_gate: could not read parents of %s", sha)
        return ()
    return tuple(spawned.danger_ok.stdout.split())


def _commit_exempts_file(
    root: Path, sha: str, file: str, ticket: Ticket, queue: TicketQueue
) -> bool:
    """True if commit `sha` (or, for a merge commit whose own subject carries
    no ticket reference, one of its parents) names another ticket (not
    `ticket`) whose own declared `scope` covers `file` -- the SCOPE001
    cross-ticket exemption (T-0108): a commit's authorship is attributed by
    the ticket id its subject references, not by whichever ticket happens to
    be running the check now.

    T-0527: a plain `git merge main` merge commit's OWN subject typically
    carries no ticket reference at all, yet `git blame` can still attribute
    a hunk to it (conflict-resolution content that differs from every
    parent, e.g. a version-bump line both sides touched) -- that content is
    still just reconciling the parents' own already-scoped work, not new
    unscoped work introduced by this check's own ticket. So a merge commit
    (more than one parent) whose subject has no usable ticket reference
    falls back to searching its PARENTS' subjects for the reference that
    actually attributes the reconciled content, instead of being treated as
    a wholly unattributed touch."""

    subjects = []
    subject = _commit_subject(root, sha)
    if subject.is_some:
        subjects.append(subject.danger_some)
    parents = _commit_parents(root, sha)
    if len(parents) > 1 and not (
        subject.is_some and _TICKET_REF_RE.search(subject.danger_some)
    ):
        for parent in parents:
            parent_subject = _commit_subject(root, parent)
            if parent_subject.is_some:
                subjects.append(parent_subject.danger_some)
    for subject_text in subjects:
        for ref in _TICKET_REF_RE.findall(subject_text):
            if ref == ticket.id:
                continue
            other = queue.tickets.get(ref)
            if other is None:
                continue
            if scope_matches(file, other.scope):
                return True
    return False


def _hunk_exempt(root: Path, hunk: Hunk, ticket: Ticket, queue: TicketQueue) -> bool:
    """True if every line of `hunk` is already committed (no working-tree-dirty
    lines) and attributable to a commit exempted per `_commit_exempts_file`."""
    start, end = hunk.span
    shas_opt = _blame_shas(root, hunk.file, start, end)
    if shas_opt.is_nothing:
        return False
    shas = shas_opt.danger_some
    if not shas or _UNCOMMITTED_SHA in shas:
        return False
    return all(
        _commit_exempts_file(root, sha, hunk.file, ticket, queue) for sha in shas
    )


def _scope_exempt_file(
    root: Path, file: str, diff: Diff, ticket: Ticket, queue: TicketQueue
) -> bool:
    """True if every hunk touching `file` in `diff` was already committed under
    another ticket's own declared scope -- fixes SCOPE001 false positives when
    ticket A's committed work still shows up in ticket B's diff against `base`
    (T-0108). Working-tree-dirty hunks are never exempt: only prior commits
    naming a scoping ticket are."""
    hunks = tuple(h for h in diff.hunks if h.file == file)
    if not hunks:
        return False
    return all(_hunk_exempt(root, hunk, ticket, queue) for hunk in hunks)


# frob:doc docs/modules/gates.md#public-api
# frob:doc docs/modules/gates.md#scope002-t-0998
# frob:ticket T-0906
# frob:tests tests/test_gates.py::TestScopePrework.test_scope001_fires_when_no_scope_declared  # noqa: E501
# frob:tests tests/test_gates.py::TestScopePrework.test_scope001_empty_scope_ledger_still_implicitly_in_scope  # noqa: E501
def scope_gate(
    diff: Diff,
    ticket: Ticket,
    snapshot: GraphSnapshot,
    *,
    root: Path | None = None,
    queue: TicketQueue | None = None,
) -> tuple[Violation, ...]:
    """SCOPE001: diff touches paths outside the active ticket's `scope`. When
    `root` and `queue` are given, a file already committed entirely under
    another ticket's own scope (its commits' subjects reference that ticket
    id) is exempt -- fixes SCOPE001 false positives when ticket A's
    already-committed work still shows up in ticket B's diff on the same
    branch (T-0108).

    An empty `ticket.scope` is deliberately NOT treated as "nothing to
    enforce" (T-0906/H1 in `docs/audits/gates-vacuous.md`): `scope_matches`
    already treats an empty scope as matching only `LEDGER_PATH` (plus a
    FEATURE ticket's implicit CLI-wiring files), so falling through to the
    normal per-file loop below already produces the correct, loud SCOPE001
    for every other touched file -- an undeclared scope is the riskiest
    ticket state (no stated intent at all) and must get MORE enforcement,
    never a silent, unconditional pass."""

    touched = sorted(_touched_files(diff))
    violations = [
        v
        for file in touched
        for v in (_scope_gate_check_file(file, ticket, diff, root, queue),)
        if v is not None
    ]
    violations.extend(_scope002_violations(ticket, snapshot, root))
    return tuple(violations)


# frob:ticket T-0998
def _scope002_violation(message: str) -> Violation:
    """One SCOPE002 finding (T-0998, WARN turn-on per the promotion
    playbook docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756)
    -- a nudge, not a hard block: unlike SCOPE001 (a diff genuinely
    touching an unscoped file), SCOPE002 fires at scope-DECLARATION time,
    before any file is touched at all, so it must never block a ticket
    that legitimately intends a narrower slice than its own doc/call
    graph suggests."""
    return Violation(
        rule="SCOPE002",
        severity=Severity.WARN,
        file="tickets.md",
        line=0,
        message=message,
    )


# frob:ticket T-0998
# frob:tests tests/test_gates.py::TestScope002ClosureGate.test_warns_on_unscoped_doc_target  # noqa: E501
# frob:tests tests/test_gates.py::TestScope002ClosureGate.test_warns_on_unscoped_private_helper  # noqa: E501
# frob:tests tests/test_gates.py::TestScope002ClosureGate.test_warns_on_unscoped_test_target  # noqa: E501
# frob:tests tests/test_gates.py::TestScope002ClosureGate.test_silent_on_closed_scope  # noqa: E501
# frob:enforces CHK-GATE-SCOPE002
def _scope002_violations(
    ticket: Ticket, snapshot: GraphSnapshot, root: Path | None
) -> tuple[Violation, ...]:
    """SCOPE002 (T-0998): scope-declaration-time doc-edge + test-edge +
    private-helper closure validation over `ticket.scope` -- the closure
    TRIPLE: code<->docs (`frob.graph.affects.scope_doc_code_gaps`,
    directions 1+2, the SAME `frob:doc`/`frob:describes` edges
    `affects()`/AFFECT001 already walk), code<->tests
    (`frob.graph.affects.scope_test_gaps`, symmetric with the doc
    direction -- scoped code implies its `frob:tests`-covering test file
    in scope, and vice versa, reusing the SAME `EdgeKind.TESTS` edges
    `_test_refs_for` already reads), and the private-helper capture
    (`frob.graph.callgraph.scope_private_helper_gaps`, direction 3, the
    shared `build_call_graph` substrate T-0288/T-0290 already use) -- no
    second traversal engine anywhere in the triple. WARN-only (T-0756
    promotion playbook: a new rule id turns on at WARN, a later ticket
    promotes it to ERROR once the real-repo false-positive rate is
    measured clean); an empty `ticket.scope` is skipped (nothing declared
    yet to validate a closure over -- `frob ticket new`'s own suggest-or-
    warn surface is where an about-to-be-created ticket gets this feedback
    BEFORE scope is even saved, this gate covers every ticket already
    carrying one). `scope_private_helper_gaps` needs `root` to parse
    source files; skipped (not fail-closed -- SCOPE002 is a nudge) when
    `root` is `None`."""
    if not ticket.scope:
        return ()
    violations = list(_scope002_edge_gap_violations(ticket, snapshot))
    violations.extend(_scope002_helper_gap_violations(ticket, snapshot, root))
    return tuple(violations)


def _scope002_add_hint(ticket_id: str, missing_file: str) -> str:
    """Shared remediation tail for every SCOPE002 finding (T-0998)."""
    return (
        f"{missing_file!r}, not in scope -- add it: "
        f"frob ticket scope {ticket_id} --add {missing_file!r}"
    )


def _scope002_edge_gap_violations(
    ticket: Ticket, snapshot: GraphSnapshot
) -> list[Violation]:
    """Doc-edge + test-edge halves of the SCOPE002 closure triple (T-0998)."""
    from frob.graph.affects import scope_doc_code_gaps, scope_test_gaps

    prefixes = {
        "code_missing_doc": "whose frob:doc target",
        "doc_missing_code": "describing",
        "code_missing_test": "whose frob:tests target",
        "test_missing_code": "covering",
    }
    site_kind = {"doc_missing_code": "doc anchor ", "test_missing_code": "test "}
    violations: list[Violation] = []
    gaps = list(scope_doc_code_gaps(snapshot, ticket.scope))
    gaps.extend(scope_test_gaps(snapshot, ticket.scope))
    for gap in gaps:
        violations.append(
            _scope002_violation(
                f"SCOPE002: {ticket.id} scope includes "
                f"{site_kind.get(gap.direction, '')}{gap.scoped_site} "
                f"{prefixes[gap.direction]} {gap.target} lives in "
                + _scope002_add_hint(ticket.id, gap.missing_file)
            )
        )
    return violations


def _scope002_helper_gap_violations(
    ticket: Ticket, snapshot: GraphSnapshot, root: Path | None
) -> list[Violation]:
    """Private-helper half of the SCOPE002 closure triple (T-0998)."""
    from frob.graph.callgraph import scope_private_helper_gaps

    if root is None:
        return []
    violations: list[Violation] = []
    for helper_gap in scope_private_helper_gaps(
        root, ticket.scope, tuple(snapshot.file_hashes)
    ):
        suggestion = (
            "add it" if helper_gap.only_used_by_scope else "review the dependency"
        )
        violations.append(
            _scope002_violation(
                f"SCOPE002: {ticket.id} scope includes {helper_gap.caller} "
                f"which calls private helper {helper_gap.callee} defined "
                f"in {helper_gap.definition_file!r}, not in scope "
                f"(probable under-capture) -- {suggestion}: frob ticket "
                f"scope {ticket.id} --add {helper_gap.definition_file!r}"
            )
        )
    return violations


# frob:enforces CHK-GATE-SCOPE001
def _scope_gate_check_file(
    file: str,
    ticket: Ticket,
    diff: Diff,
    root: Path | None,
    queue: TicketQueue | None,
) -> Violation | None:
    """The SCOPE001 `Violation` for one touched `file`, or None when it
    matches `ticket.scope` (T-0446: a FEATURE ticket's CLI-wiring files are
    implicitly included here too) or is exempt (already committed under
    another ticket's own scope, T-0108)."""
    if scope_matches(file, ticket.scope, kind=ticket.kind):
        return None
    if (
        root is not None
        and queue is not None
        and _scope_exempt_file(root, file, diff, ticket, queue)
    ):
        _log.debug(
            "SCOPE001: %s exempt for %s (committed under another ticket's scope)",
            file,
            ticket.id,
        )
        return None
    _log.debug("SCOPE001: %s outside %s's scope", file, ticket.id)
    return Violation(
        rule="SCOPE001",
        severity=Severity.ERROR,
        file=file,
        line=0,
        message=(
            f"SCOPE001: {file} is outside {ticket.id}'s declared scope; "
            f"extend the ticket's scope or open a new ticket for this file"
        ),
    )


# frob:enforces CHK-GATE-PRE001
def _pre001(ticket: Ticket, message: str) -> tuple[Violation, ...]:
    """A single PRE001 violation for `ticket` carrying `message`."""
    return (
        Violation(
            rule="PRE001",
            severity=Severity.ERROR,
            file=f"tickets/{ticket.id}",
            line=0,
            message=message,
        ),
    )


# frob:doc docs/modules/gates.md#public-api
def prework_gate(
    ticket: Ticket, snapshot: GraphSnapshot, sweep: Option[PreworkSweep] = Nothing()
) -> tuple[Violation, ...]:
    """PRE001: ticket moved to in-progress without a recorded, current pre-work sweep.

    **Deviation from docs/modules/gates.md's exact signature** `(ticket, snapshot)`: the
    sweep is loaded state (from `.frob/prework/<id>.json`, see gates/_prework.py),
    and gates must not perform IO, so `run_gates` loads it and passes it in as an
    optional third argument rather than this function reaching into the
    filesystem itself.
    """
    if ticket.state != TicketState.IN_PROGRESS:
        return ()
    if sweep.is_nothing:
        _log.debug("PRE001: %s in-progress with no recorded sweep", ticket.id)
        return _pre001(
            ticket,
            f"PRE001: {ticket.id} is in-progress with no recorded pre-work "
            f"sweep; run: frob ticket start {ticket.id}",
        )
    current_digest = _scope_digest(ticket, snapshot)
    if sweep.danger_some.digest != current_digest:
        _log.debug("PRE001: %s sweep is stale (digest moved)", ticket.id)
        return _pre001(
            ticket,
            f"PRE001: {ticket.id}'s recorded pre-work sweep is stale against "
            f"the current scope; run: frob ticket start {ticket.id} again",
        )
    # T-0584: a PARTIAL sweep (one that ran out of its bounded budget before
    # finishing every scope pattern -- gates/_prework.py's sweep_ticket) is
    # still provisionally clean here as long as its digest matches the
    # ticket's CURRENT scope: the whole point of bounding the sweep is that
    # PRE001 must not itself demand the very completed sweep a slow mount
    # could not produce in one foreground-budget-sized call. `frob ticket
    # sweep <id>` resumes the remaining patterns on the next call; this is
    # not a permanent bypass, just a way for that resumption to happen
    # across multiple bounded calls instead of never happening at all.
    if sweep.danger_some.partial:
        _log.debug(
            "PRE001: %s sweep is partial (%d pattern(s) pending) but digest "
            "matches -- provisionally clean, resume with `frob ticket sweep %s`",
            ticket.id,
            len(sweep.danger_some.pending_patterns),
            ticket.id,
        )
    return ()


def _flatten_edges(edges_by_target: dict[str, list[Edge]]) -> list[tuple[str, Edge]]:
    """Flatten a `{target: [edge]}` index to `[(target, edge)]` pairs (built once)."""
    return [
        (target, edge) for target, edges in edges_by_target.items() for edge in edges
    ]


# ---------------------------------------------------------------------------
# TEST001 / TEST002
# ---------------------------------------------------------------------------


def _test001_002_one(
    record,  # noqa: ANN001
    unit_edges: dict[str, list[Edge]],
    tests: CollectedTests,
    cfg: TestPolicy,
    snapshot: GraphSnapshot,
    coverage: Option[CoverageData] = Nothing(),
) -> Violation | None:
    """The TEST001/TEST002 verdict for one public function/method, or None."""
    edges = unit_edges.get(record.symref, [])
    valid = _valid_edges(edges, tests, snapshot)
    # An explicit frob:tests edge is authoritative -- judge it by its valid
    # (collected) count. Only when NO explicit edge exists does a
    # conventionally named test (test_<name>) count toward coverage (T-0018).
    # T-0307: count actual collected cases (parametrize expansions), not
    # edges -- len(valid) undercounts a parametrized test to 1.
    effective = (
        _case_count(valid, tests, Path(snapshot.root))
        if edges
        else _inferred_unit_cases(record.symref, tests)
    )
    if effective == 0 and not edges:
        return _test001_no_unit_test(record)
    if effective < cfg.min_unit_cases:
        return _test002_below_min(record, effective, cfg)
    if cfg.require_branch_coverage_for_test001 and coverage.is_some:
        zero_cov = _test001_zero_measured_branch_coverage(record, coverage.danger_some)
        if zero_cov is not None:
            return zero_cov
    return None


# frob:ticket T-0589
def _test001_zero_measured_branch_coverage(
    record,  # noqa: ANN001
    data: CoverageData,
) -> Violation | None:
    """T-0589 (opt-in via `TestPolicy.require_branch_coverage_for_test001`):
    `record` passed the name/edge check above, but `coverage.xml` proves its
    branch coverage is measured-and-zero -- the `_test005_symbols`/T-0557
    "file measured, symbol never executed" signal, reused here to promote
    TEST001 credit from "a test is bound by name/edge" to "that binding
    actually ran the symbol at least once". `None` (no override) when the
    symbol was never measured at all (`data.symbol_branch` has no entry AND
    its file is absent from `data.module_line`) -- a measurement gap is
    TEST006's territory, not proof this symbol's binding is vacuous."""
    pct = data.symbol_branch.get(record.symref)
    if pct is None:
        if record.id.path not in data.module_line:
            return None
        pct = 0.0
    if pct > 0.0:
        return None
    _log.debug(
        "TEST001: %s has a satisfying name/edge match but 0%% measured "
        "branch coverage (T-0589)",
        record.symref,
    )
    leaf = _snake(record.id.qualname.rsplit(".", 1)[-1])
    return Violation(
        rule="TEST001",
        severity=Severity.ERROR,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"TEST001: {record.symref} has a name/edge-matched unit test, "
            "but coverage.xml shows 0% measured branch coverage -- the "
            "bound test never actually executes this symbol; add: "
            f'frob:tests {record.symref} kind="unit" bound to a test that '
            f"really calls it (or name a test test_{leaf} that does)"
        ),
    )


# frob:enforces CHK-GATE-TEST001
def _test001_no_unit_test(record) -> Violation:  # noqa: ANN001
    """TEST001: `record` is public with no unit edge or convention match."""
    _log.debug("TEST001: %s has no unit edge or convention match", record.symref)
    leaf = _snake(record.id.qualname.rsplit(".", 1)[-1])
    return Violation(
        rule="TEST001",
        severity=Severity.ERROR,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"TEST001: {record.symref} is public with no unit test; "
            f'add: frob:tests {record.symref} kind="unit" '
            f"(or name a test test_{leaf})"
        ),
    )


# frob:enforces CHK-GATE-TEST002
def _test002_below_min(record, effective: int, cfg: TestPolicy) -> Violation:  # noqa: ANN001
    """TEST002: `record` has fewer collected unit cases than `cfg.min_unit_cases`."""
    _log.debug(
        "TEST002: %s has %d/%d unit cases",
        record.symref,
        effective,
        cfg.min_unit_cases,
    )
    return Violation(
        rule="TEST002",
        severity=Severity.WARN,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"TEST002: {record.symref} has {effective} collected unit "
            f"case(s), below min_unit_cases={cfg.min_unit_cases}; "
            f'add more: frob:tests {record.symref} kind="unit"'
        ),
    )


def _test001_002(
    snapshot: GraphSnapshot,
    tests: CollectedTests,
    cfg: TestPolicy,
    coverage: Option[CoverageData] = Nothing(),
) -> tuple[Violation, ...]:
    """TEST001 (no unit edge) and TEST002 (fewer than min_unit_cases valid edges).

    `.strata` design-file declarations (`flow`, `operation`, `scenario` --
    mapped to `SymbolKind.FUNCTION`/`METHOD` by `_walk_strata.py`'s
    best-effort analogy) are exempt (T-0168): a "unit test" for a design
    construct has no defined meaning -- pytest cannot exercise a `flow`,
    only strata's own prover/audit machinery (`frob sys audit`,
    self-conformance) verifies it means what it claims. Demanding a
    `frob:tests` edge here would be a semantically confused warning class,
    consistent with T-0164's COV002 precedent that a `.strata` file is one
    design artifact governed by design-level gates, not pytest bindings.

    `coverage` (T-0589, default `Nothing()`) additionally ties TEST001
    credit to real per-symbol branch coverage when
    `cfg.require_branch_coverage_for_test001` is set -- see
    `_test001_zero_measured_branch_coverage`.
    """
    unit_edges = _unit_test_edges(snapshot, "unit")
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or is_test_file(record.id.path)
            or record.id.path.endswith(".strata")
        ):
            continue
        verdict = _test001_002_one(record, unit_edges, tests, cfg, snapshot, coverage)
        if verdict is not None:
            violations.append(verdict)
    return tuple(violations)


# ---------------------------------------------------------------------------
# TEST014
# ---------------------------------------------------------------------------


# frob:ticket T-0598
def _test014_group_by_leaf(
    snapshot: GraphSnapshot,
    tests: CollectedTests,
    unit_edges: dict[str, list[Edge]],
) -> dict[str, list[tuple[str, str, frozenset[str]]]]:
    """Every convention-fallback-only public symbol, grouped by its
    snake-cased leaf name, alongside the collected test node ids that
    convention-match it (`_test014_ambiguous_convention`'s grouping phase,
    split out for ARCH001 -- T-0598)."""
    by_leaf: dict[str, list[tuple[str, str, frozenset[str]]]] = {}
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or is_test_file(record.id.path)
            or record.id.path.endswith(".strata")
            or unit_edges.get(record.symref)
        ):
            continue
        _, _, qualname = record.symref.partition("::")
        leaf = _snake(qualname.rsplit(".", 1)[-1])
        if len(leaf) < 3:
            continue
        token = re.compile(rf"(^|[^a-z0-9]){re.escape(leaf)}([^a-z0-9]|$)")
        # T-0949: same `_leaf_snake_index` memo as `_inferred_unit_cases`/
        # `_test015_record_violation` -- avoid a fresh `_snake()` per node
        # id for every symbol (this loop's own outer iteration).
        # frob:waive PERF008 reason="token is a compiled re.Pattern built once just \
        # above (per outer leaf); .search(node_leaf) is a plain regex match with no \
        # I/O. PERF008 resolves the bare method name 'search' by name-only \
        # coincidence to an unrelated same-named function that genuinely reaches \
        # walk_pruned elsewhere in the repo -- a resolver ambiguity, not a real \
        # fs-walk on this call. Tracked as a resolver precision follow-up \
        # (T-1041's Done report)"  # noqa: E501
        matched = frozenset(
            node
            for node, node_leaf in _leaf_snake_index(tests)
            if token.search(node_leaf)
        )
        if matched:
            by_leaf.setdefault(leaf, []).append(
                (record.symref, record.id.path, matched)
            )
    return by_leaf


# frob:ticket T-0547
# frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_fires_on_cross_file_same_test_collision  # noqa: E501
# frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_silent_when_symbol_has_explicit_edge  # noqa: E501
# frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_silent_when_no_leaf_name_collision  # noqa: E501
# frob:enforces CHK-GATE-TEST014
def _test014_ambiguous_convention(
    snapshot: GraphSnapshot, tests: CollectedTests
) -> tuple[Violation, ...]:
    """TEST014 (warn): `_inferred_unit_cases`'s naming-convention fallback
    matches by snake-cased leaf name alone, no module/path binding (docs/
    audits/gates-accounting.md B6/E6, T-0547) -- two different public
    functions named the same thing in different files can both clear
    TEST001 off ONE test that only actually exercises one of them.

    A compat survey against this repo itself (T-0547's Done report has the
    numbers) found that a blanket "test file must share a top-level
    directory with the symbol's file" tightening breaks ~100% of the
    convention-fallback matches here -- this repo's `tests/` tree does not
    mirror `src/frob/<pkg>/` layout closely enough for that correlation to
    be sound as a default. So this gate does NOT withdraw or gate TEST001
    credit (unlike TEST013's analogous restraint for the same reason);
    it only makes the ambiguity itself loud and auditable: two or more
    DIFFERENT files' public symbols sharing a leaf name, relying only on
    the convention fallback (no explicit `frob:tests` edge on either), and
    credited by at least one of the SAME collected test node ids -- the
    exact structural shape of the audit's `def parse()` repro. Fixing a
    specific finding here is either adding an explicit `frob:tests` edge
    to disambiguate, or renaming one of the colliding symbols.
    """
    unit_edges = _unit_test_edges(snapshot, "unit")
    by_leaf = _test014_group_by_leaf(snapshot, tests, unit_edges)

    violations: list[Violation] = []
    for leaf, entries in sorted(by_leaf.items()):
        if len({path for _, path, _ in entries}) < 2:
            continue  # same leaf, but all in one file -- not the B6 shape
        for i, (symref_a, _, matched_a) in enumerate(entries):
            for symref_b, _, matched_b in entries[i + 1 :]:
                # frob:waive PERF004 reason="differs per pair, fresh work not a re-sort"  # noqa: E501
                shared = sorted(matched_a & matched_b)
                if not shared:
                    continue
                violations.append(
                    Violation(
                        rule="TEST014",
                        severity=Severity.WARN,
                        file=symref_a.split("::", 1)[0],
                        line=0,
                        message=(
                            f"TEST014: {symref_a} and {symref_b} share leaf name "
                            f"'{leaf}' and are both credited toward TEST001 by "
                            f"the same convention-matched test(s) ({shared[0]}"
                            f"{', ...' if len(shared) > 1 else ''}) -- at most "
                            "one is likely actually exercised; add an explicit "
                            'frob:tests edge kind="unit" to disambiguate'
                        ),
                    )
                )
    return tuple(violations)


# ---------------------------------------------------------------------------
# TEST015
# ---------------------------------------------------------------------------


# frob:ticket T-0548
# frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_fires_on_no_op_test_body  # noqa: E501
# frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_silent_when_any_matching_test_asserts  # noqa: E501
# frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_silent_when_no_test_matches_at_all  # noqa: E501
# frob:enforces CHK-GATE-TEST015
def _test015_vacuous_credit(
    snapshot: GraphSnapshot, tests: CollectedTests
) -> tuple[Violation, ...]:
    """TEST015 (warn): a public symbol clears TEST001 (docs/audits/
    gates-accounting.md B1/E1, T-0548) using ONLY test(s) with no
    assertion-shaped construct at all (`_has_assertion_evidence`, T-0549's
    existing heuristic) -- `def test_myfunc(): pass` is real, blocking
    TEST001 credit today, and nothing inspects whether it asserts anything.

    A dedicated ticket (T-0548) already scoped the RIGHT-WAY fix as
    large and cross-cutting: tying TEST001 credit to nonzero per-symbol
    branch coverage, or promoting TEST005 to ERROR, touches TEST002/003/
    004/005/009's severities and interactions together, plus the
    legacy-adoption WARN campaign `frob.toml` already documents -- not a
    change to make blind. This gate reuses T-0549's existing, already-
    proven `_has_assertion_evidence` heuristic (extended here from
    "disambiguate a parametrize inflation" to "the single test IS the only
    credit source") to make the exact B1 repro loud and auditable
    WITHOUT changing what TEST001 itself blocks on -- the same restrained
    pattern as TEST013/TEST014's WARN-only landings this same audit pass.
    """
    root = Path(snapshot.root)
    unit_edges = _unit_test_edges(snapshot, "unit")
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        violation = _test015_record_violation(root, record, tests, snapshot, unit_edges)
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:ticket T-0598
def _test015_record_violation(
    root: Path,
    record: SymbolRecord,
    tests: CollectedTests,
    snapshot: GraphSnapshot,
    unit_edges: dict[str, list[Edge]],
) -> Violation | None:
    """One public symbol's TEST015 finding, or `None` if it is out of scope
    or its credit-granting test node ids include at least one real
    assertion (`_test015_vacuous_credit`'s per-record body, split out for
    ARCH001 -- T-0598)."""
    if (
        not record.public
        or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
        or is_test_file(record.id.path)
        or record.id.path.endswith(".strata")
    ):
        return None
    edges = unit_edges.get(record.symref, [])
    node_ids: set[str] = set()
    if edges:
        # T-0949: same `_case_ids_by_base` memo `_node_id_collected`/
        # `_case_count` use, instead of a fresh full-`node_ids` scan per edge.
        for edge in _valid_edges(edges, tests, snapshot):
            base = _symref_to_nodeid(edge.src)
            if base in tests.node_ids:
                node_ids.add(base)
            node_ids.update(_case_ids_by_base(tests.node_ids).get(base, ()))
    else:
        _, _, qualname = record.symref.partition("::")
        leaf = _snake(qualname.rsplit(".", 1)[-1])
        if len(leaf) < 3:
            return None
        token = re.compile(rf"(^|[^a-z0-9]){re.escape(leaf)}([^a-z0-9]|$)")
        # T-0949: same `_leaf_snake_index` memo `_inferred_unit_cases` uses,
        # avoiding a fresh `_snake()` per node id for every symbol here too.
        node_ids = {
            n for n, node_leaf in _leaf_snake_index(tests) if token.search(node_leaf)
        }
    if not node_ids:
        return None
    if any(_has_assertion_evidence(root, n.split("[", 1)[0]) for n in node_ids):
        return None
    example = sorted(node_ids)[0]
    return Violation(
        rule="TEST015",
        severity=Severity.WARN,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"TEST015: {record.symref} clears TEST001 only via "
            f"test(s) with no assertion-shaped construct ({example}"
            f"{', ...' if len(node_ids) > 1 else ''}) -- likely a "
            "vacuous/no-op test; add a real assertion or bind an "
            'explicit frob:tests edge kind="unit" to one'
        ),
    )


# ---------------------------------------------------------------------------
# TEST003
# ---------------------------------------------------------------------------


def _public_packages(snapshot: GraphSnapshot) -> list[str]:
    """Every `src/<pkg>/<subpkg>` package that contains a public, non-test symbol.

    `.strata` design-file declarations are excluded (T-0225), matching the
    `_test001_002` exemption (T-0168): a design construct's proof obligation
    is e2e-shaped (`_test009`), not "interface has N integration tests" --
    counting `design/` as a package here just misapplied TEST003's
    pytest-integration semantics to a directory that owns no pytest surface
    at all.
    """
    packages: dict[str, bool] = {}
    for record in snapshot.symbols.values():
        if (
            record.public
            and not is_test_file(record.id.path)
            and not record.id.path.endswith(".strata")
        ):
            packages.setdefault(_interface_package(record.id.path), True)
    return list(packages)


def _edges_for_package(all_pairs: list[tuple[str, Edge]], package: str) -> list[Edge]:
    """Integration edges whose target is `package` or lives under it."""
    prefix = package.rstrip("/") + "/"
    return [
        edge
        for target, edge in all_pairs
        if target == package or (target.startswith(prefix))
    ]


def _test003(
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
) -> tuple[Violation, ...]:
    """TEST003: every package with public symbols owes `min_integration` edges.

    **Interface derivation, alpha semantics**: docs/modules/gates.md describes
    interfaces
    as "packages whose public symbols are imported by another package." The
    graph does not track cross-file import edges, so alpha instead treats every
    `src/<pkg>/<subpkg>` directory that contains at least one public symbol as
    an interface owing integration tests -- the honest over-approximation the
    task explicitly allows in place of real import-graph derivation.
    """
    all_pairs = _flatten_edges(_test_edges(snapshot, "integration"))
    ordered_packages = sorted(_public_packages(snapshot))
    violations = [
        v
        for package in ordered_packages
        for v in (_test003_check_package(package, all_pairs, tests, cfg, snapshot),)
        if v is not None
    ]
    return tuple(violations)


# frob:enforces CHK-GATE-TEST003
def _test003_check_package(
    package: str,
    all_pairs: list[tuple[str, Edge]],
    tests: CollectedTests,
    cfg: TestPolicy,
    snapshot: GraphSnapshot,
) -> Violation | None:
    """The TEST003 `Violation` for one interface `package`, or None when it
    already has at least `cfg.min_integration` valid edges."""
    valid = _valid_edges(_edges_for_package(all_pairs, package), tests, snapshot)
    # T-0307: count actual collected cases (parametrize expansions), not
    # edges -- a parametrized integration test must count each case.
    count = _case_count(valid, tests, Path(snapshot.root))
    if count >= cfg.min_integration:
        return None
    _log.debug(
        "TEST003: %s has %d/%d integration edges",
        package,
        count,
        cfg.min_integration,
    )
    return Violation(
        rule="TEST003",
        severity=Severity.WARN,
        file=package,
        line=0,
        message=(
            f"TEST003: interface {package} has {count} integration "
            f"test(s), below min_integration={cfg.min_integration}; "
            f'add: frob:tests {package} kind="integration"'
        ),
    )


# ---------------------------------------------------------------------------
# TEST009
# ---------------------------------------------------------------------------


def _design_files(snapshot: GraphSnapshot) -> list[str]:
    """Every NON-TEST `.strata` design file that declares at least one public
    flow/boundary/operation/scenario construct (`_walk_strata.py`'s
    `_KEYWORD_KIND` mapping onto `FUNCTION`/`METHOD`).

    Test-fixture `.strata` files (litmus/parser fixtures under a tests dir)
    are excluded (T-0225 follow-up): TEST009 owes an e2e binding to a
    DEPLOYABLE design model, but a litmus fixture is test DATA exercised
    through its own covering pytest suite, not a system that owes its own
    e2e obligation -- mirroring `_test001_002`/`_public_packages`' own
    `is_test_file` exemptions."""
    files: dict[str, bool] = {}
    for record in snapshot.symbols.values():
        if (
            record.public
            and record.id.path.endswith(".strata")
            and not is_test_file(record.id.path)
        ):
            files.setdefault(record.id.path, True)
    return list(files)


def _edges_for_design_file(
    all_pairs: list[tuple[str, Edge]], design_file: str
) -> list[Edge]:
    """e2e edges whose target is `design_file` itself or a symbol declared in it."""
    prefix = design_file + "::"
    return [
        edge
        for target, edge in all_pairs
        if target == design_file or target.startswith(prefix)
    ]


# frob:enforces CHK-GATE-TEST009
def _test009(
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
) -> tuple[Violation, ...]:
    """TEST009: every `.strata` design file owes `min_design_e2e` e2e edges (T-0225).

    T-0168 exempted design-file `flow`/`boundary`/`operation`/`scenario`
    declarations from TEST001/TEST002 (a "unit test" for a design construct
    has no defined meaning), and T-0225 exempts the same declarations from
    TEST003 (`_public_packages`) for the identical reason -- `design/` owns
    no pytest surface at all, so package-level integration-test counting
    misapplies TEST003's semantics to it. That is not the same as "design
    ids owe no test obligation whatsoever": strata's own conformance
    machinery (`frob sys audit`, self-conformance) is exercised end-to-end,
    so the correct binding shape is `kind="e2e"`, not unit/integration.
    This mirrors TEST004's per-`[[system]]` e2e floor but scopes to `.strata`
    files instead of declared `[[system]]` entries, and treats a whole
    design file as one artifact needing coverage (consistent with T-0164's
    COV002 precedent), not each construct individually.
    """
    all_pairs = _flatten_edges(_test_edges(snapshot, "e2e"))
    violations: list[Violation] = []
    for design_file in sorted(_design_files(snapshot)):
        valid = _valid_edges(
            _edges_for_design_file(all_pairs, design_file), tests, snapshot
        )
        count = _case_count(valid, tests, Path(snapshot.root))
        if count >= cfg.min_design_e2e:
            continue
        _log.debug(
            "TEST009: %s has %d/%d e2e edges", design_file, count, cfg.min_design_e2e
        )
        violations.append(
            Violation(
                rule="TEST009",
                severity=Severity.WARN,
                file=design_file,
                line=0,
                message=(
                    f"TEST009: design file {design_file} has {count} e2e "
                    f"test(s), below min_design_e2e={cfg.min_design_e2e}; "
                    f'add: frob:tests {design_file} kind="e2e"'
                ),
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# TEST007
# ---------------------------------------------------------------------------


def _uses_contract_pairs(snapshot: GraphSnapshot) -> set[tuple[str, str]]:
    """Cross-package `(consumer, provider)` pairs from `frob:uses-contract` edges."""
    pairs: set[tuple[str, str]] = set()
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.USES_CONTRACT:
            continue
        consumer = _interface_package(edge.src.split("::", 1)[0])
        provider = _interface_package(edge.target.split("::", 1)[0])
        if consumer != provider:
            pairs.add((consumer, provider))
    return pairs


def _consumer_leaf(consumer: str) -> str:
    """The package leaf tests conventionally mirror (src/app -> "app")."""
    leaf = PurePosixPath(consumer).name
    if leaf.endswith(".py"):
        leaf = PurePosixPath(consumer).parent.name
    return leaf


def _pair_covered(
    consumer_leaf: str,
    provider: str,
    all_pairs: list[tuple[str, Edge]],
    tests: CollectedTests,
) -> bool:
    """True if an integration test for `provider` also names the consumer leaf."""
    prefix = provider.rstrip("/") + "/"
    for target, edge in all_pairs:
        if not (target == provider or target.startswith(prefix)):
            continue
        if not _node_id_collected(_symref_to_nodeid(edge.src), tests.node_ids):
            continue
        test_path = edge.src.split("::", 1)[0]
        if consumer_leaf in PurePosixPath(test_path).parts or (
            f"test_{consumer_leaf}" in test_path
        ):
            return True
    return False


# frob:ticket T-0017
def _test007_pairs(
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
) -> tuple[Violation, ...]:
    """TEST007: a declared cross-package dependency owes a pairwise
    integration test.

    Where a `frob:uses-contract` edge crosses a package boundary, that
    specific (consumer, provider) boundary must be covered by an integration
    test that names BOTH packages. Opt-in via `[testing].pair_integration`.
    """
    if not cfg.pair_integration:
        return ()
    all_pairs = _flatten_edges(_test_edges(snapshot, "integration"))
    ordered_pairs = sorted(_uses_contract_pairs(snapshot))
    violations = [
        v
        for consumer, provider in ordered_pairs
        for v in (_test007_check_pair(consumer, provider, all_pairs, tests),)
        if v is not None
    ]
    return tuple(violations)


# frob:enforces CHK-GATE-TEST007
def _test007_check_pair(
    consumer: str,
    provider: str,
    all_pairs: list[tuple[str, Edge]],
    tests: CollectedTests,
) -> Violation | None:
    """The TEST007 `Violation` for one `(consumer, provider)` dependency
    pair, or None when the boundary is already covered."""
    if _pair_covered(_consumer_leaf(consumer), provider, all_pairs, tests):
        return None
    _log.debug("TEST007: %s -> %s boundary untested", consumer, provider)
    return Violation(
        rule="TEST007",
        severity=Severity.WARN,
        file=consumer,
        line=0,
        message=(
            f"TEST007: the {consumer} -> {provider} dependency has no "
            f"integration test covering that boundary; add an "
            f"integration test in {consumer} with frob:tests {provider} "
            f'kind="integration"'
        ),
    )


# ---------------------------------------------------------------------------
# TEST004 / TEST005 / TEST006
# ---------------------------------------------------------------------------


# frob:enforces CHK-GATE-TEST004
def _test004(
    systems: tuple[SystemSpec, ...], snapshot: GraphSnapshot, tests: CollectedTests
) -> tuple[Violation, ...]:
    """TEST004: a declared `[[system]]` has fewer than its `min_e2e` e2e edges."""
    e2e_edges = _test_edges(snapshot, "e2e")
    violations: list[Violation] = []
    for system in systems:
        valid = _valid_edges(e2e_edges.get(system.id, []), tests, snapshot)
        if len(valid) < system.min_e2e:
            _log.debug(
                "TEST004: %s has %d/%d e2e edges", system.id, len(valid), system.min_e2e
            )
            violations.append(
                Violation(
                    rule="TEST004",
                    severity=Severity.ERROR,
                    file=f"[[system]] {system.id}",
                    line=0,
                    message=(
                        f"TEST004: system {system.id} has {len(valid)} e2e test(s), "
                        f"below min_e2e={system.min_e2e}; "
                        f'add: frob:tests {system.id} kind="e2e"'
                    ),
                )
            )
    return tuple(violations)


# frob:ticket T-0557
# frob:tests tests/test_gates.py::TestTestGate.test_test005_unmeasured_symbol_in_measured_file_flags_as_zero  # noqa: E501
# frob:tests tests/test_gates.py::TestTestGate.test_test005_symbol_in_unmeasured_file_still_skipped  # noqa: E501
# frob:ticket T-1205
# T-1205 acceptance[1]: a TEST005 finding computed against a stale
# coverage.xml (`data.stale_by_mtime` -- the report predates a tracked
# source change TEST011 already warns about) must never be reported as an
# unqualified current fact. The 2026-07-31 incident this ticket exists to
# prevent (T-1293: an agent trusted a 23-hour-stale stamp, closed a ticket
# having fixed 1 of 64 real findings) happened precisely because a stale
# finding read exactly like a fresh one. Every TEST005 message gets this
# prefix whenever the coverage data behind it is stale, so the disclosure
# travels with the finding itself rather than depending on a reader
# separately noticing TEST011's own advisory line.
_STALE_DISCLOSURE_PREFIX = "[STALE COVERAGE] "


def _test005_symbols(
    snapshot: GraphSnapshot, data: CoverageData, cfg: TestPolicy
) -> list[Violation]:
    """TEST005 per-symbol branch-coverage floor.

    Skips test-file symbols exactly like TEST001/TEST002 do (T-0301): a
    test-file helper/fixture is not a public interface TEST005's floor is
    meant to police, and measuring it forced env-gated test fixtures into
    noise waivers just to stay green (lithos FROBLEMS 2026-07-19).

    T-0557 (B4): `data.symbol_branch` has no entry at all for a symbol that
    was NEVER EXECUTED (no line of it ever ran, so coverage.py recorded
    nothing to average) -- previously treated the same as a symbol whose
    whole FILE was never measured (excluded from `--cov`, a generated
    source, or simply not imported by the suite) and silently skipped both.
    Those are different failure modes: a symbol in a file coverage.xml DOES
    have data for (`record.id.path in data.module_line`) but with no entry
    of its own is real, unexecuted dead code and must be treated as 0%
    branch coverage, not waved through. A symbol whose file has no coverage
    data at all is still skipped here -- that is a measurement gap
    (TEST006/module_join_fraction's territory), not proof the symbol itself
    is uncovered, and flagging it would conflate "never measured" with
    "measured and failing."
    """
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or is_test_file(record.id.path)
        ):
            continue
        pct = data.symbol_branch.get(record.symref)
        if pct is None and record.id.path in data.module_line:
            pct = 0.0
        if pct is not None and pct < cfg.unit_branch_cov:
            violations.append(
                _test005_symbol_violation(record, pct, cfg, data.stale_by_mtime)
            )
    return violations


# frob:enforces CHK-GATE-TEST005
def _test005_symbol_violation(
    record,
    pct: float,
    cfg: TestPolicy,
    stale: bool = False,  # noqa: ANN001
) -> Violation:
    """A single TEST005 per-symbol branch-coverage-floor violation.

    T-1205: `stale` (`CoverageData.stale_by_mtime`) prepends
    `_STALE_DISCLOSURE_PREFIX` to the message when the coverage.xml this
    finding was computed from predates a tracked source change -- the
    finding is disclosed as possibly-outdated rather than reported as an
    unqualified current fact.
    """
    _log.debug(
        "TEST005: %s branch cov %.1f%% < %d%% (stale=%s)",
        record.symref,
        pct,
        cfg.unit_branch_cov,
        stale,
    )
    prefix = _STALE_DISCLOSURE_PREFIX if stale else ""
    return Violation(
        rule="TEST005",
        severity=Severity.WARN,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"{prefix}TEST005: {record.symref} branch coverage {pct:.1f}% below "
            f"unit_branch_cov={cfg.unit_branch_cov}%; add tests, then: "
            f"make coverage"
        ),
        symref=record.symref,
    )


def _test005_modules(data: CoverageData, cfg: TestPolicy) -> list[Violation]:
    """TEST005 per-module line-coverage floor."""
    violations: list[Violation] = []
    prefix = _STALE_DISCLOSURE_PREFIX if data.stale_by_mtime else ""
    for module, pct in data.module_line.items():
        if pct < cfg.module_line_cov:
            _log.debug(
                "TEST005: %s line cov %.1f%% < %d%% (stale=%s)",
                module,
                pct,
                cfg.module_line_cov,
                data.stale_by_mtime,
            )
            violations.append(
                Violation(
                    rule="TEST005",
                    severity=Severity.WARN,
                    file=module,
                    line=0,
                    message=(
                        f"{prefix}TEST005: {module} line coverage {pct:.1f}% below "
                        f"module_line_cov={cfg.module_line_cov}%; add tests, then: "
                        f"make coverage"
                    ),
                )
            )
    return violations


def _test005_systems(
    systems: tuple[SystemSpec, ...], data: CoverageData, cfg: TestPolicy
) -> list[Violation]:
    """TEST005 per-system aggregate line-coverage floor."""
    violations: list[Violation] = []
    for system in systems:
        relevant = [
            pct
            for path, pct in data.module_line.items()
            if any(_glob_prefix_match(path, glob) for glob in system.paths)
        ]
        if not relevant:
            continue
        avg = sum(relevant) / len(relevant)
        if avg < cfg.system_line_cov:
            violations.append(
                _test005_system_violation(system, avg, cfg, data.stale_by_mtime)
            )
    return violations


def _test005_system_violation(
    system: SystemSpec, avg: float, cfg: TestPolicy, stale: bool = False
) -> Violation:
    """A single TEST005 per-system aggregate line-coverage-floor violation.

    T-1205: `stale` prepends `_STALE_DISCLOSURE_PREFIX`, same as
    `_test005_symbol_violation` -- see that function's docstring.
    """
    _log.debug(
        "TEST005: system %s line cov %.1f%% < %d%% (stale=%s)",
        system.id,
        avg,
        cfg.system_line_cov,
        stale,
    )
    prefix = _STALE_DISCLOSURE_PREFIX if stale else ""
    return Violation(
        rule="TEST005",
        severity=Severity.WARN,
        file=f"[[system]] {system.id}",
        line=0,
        message=(
            f"{prefix}TEST005: system {system.id} line coverage {avg:.1f}% below "
            f"system_line_cov={cfg.system_line_cov}%; add tests, then: "
            f"make coverage"
        ),
    )


# frob:ticket T-0148
# TEST008 catches a silent-death condition: `_coverage.py::_parse_classes`
# tries every `<sources><source>` root Cobertura declared, then a
# bare-filename fallback, before giving up -- `data.root_join_ok` is only
# False when every one of those strategies resolved zero `<class>`
# filenames against a real path. Without this check TEST005 would just
# report "0 modules measured" and every consumer of `CoverageData` would
# quietly treat this repo as having no coverage at all, rather than a real
# "nothing to report" state -- so it is always an ERROR: this gate ships in
# many sibling repos with different package layouts, and a hardcoded or
# wrong root here must fail loudly, never degrade to a quiet zero.
# frob:enforces CHK-GATE-TEST008
def _test008_unjoined_root(data: CoverageData) -> tuple[Violation, ...]:
    """TEST008: coverage.xml carried real data but NONE of it joined to a
    known repo path (see the comment above)."""
    if data.root_join_ok:
        return ()
    tried = ", ".join(r or "(bare filename)" for r in data.attempted_roots)
    return (
        Violation(
            rule="TEST008",
            severity=Severity.ERROR,
            file="coverage.xml",
            line=0,
            message=(
                "TEST008: coverage.xml has class data but none of it joined "
                f"to a known repo path via any of the {len(data.attempted_roots)} "
                f"root(s) tried ({tried}); TEST005 coverage floors are "
                "silently measuring nothing -- check pytest-cov's --cov= "
                "target against this repo's real package layout"
            ),
        ),
    )


def _test005(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST005: measured coverage below a per-symbol, per-module, or
    per-system floor (see `_exclude_filtered_coverage` for why the raw
    `coverage.xml` data is re-filtered before use)."""
    if coverage.is_nothing:
        return ()
    data = _exclude_filtered_coverage(coverage.danger_some, snapshot)
    return (
        *_test008_unjoined_root(data),
        *_test011_freshness(data),
        *_test012_lock(snapshot, data),
        *_test005_symbols(snapshot, data, cfg),
        *_test005_modules(data, cfg),
        *_test005_systems(systems, data, cfg),
    )


# frob:ticket T-0464
_TEST011_JOIN_FLOOR = 0.5


# frob:enforces CHK-GATE-TEST011
def _test011_freshness(data: CoverageData) -> tuple[Violation, ...]:
    """TEST011 (warn): coverage.xml looks stale or deflated relative to the
    working tree it is supposed to measure.

    `CoverageData.source_sha` only hashes coverage.xml itself, not the
    source it measured -- a coverage.xml regenerated by a run that silently
    dropped subprocess coverage (T-0464's root cause) carries a
    fresh-looking sha with stale/deflated data underneath. Two independent,
    cheap-to-compute signals catch that: `stale_by_mtime` (coverage.xml is
    older than the newest known source file) and `module_join_fraction`
    (coverage.xml's `<class>` entries joined to far fewer known modules
    than the snapshot actually has -- the fingerprint of a run that only
    measured the main pytest process and never merged subprocess data).
    WARN, not ERROR: this is advisory triage pointing at `make coverage`,
    not a hard floor -- TEST005/TEST006 already carry the enforcement
    teeth this ticket's part 1 fix restores the trustworthiness of.
    """
    violations: list[Violation] = []
    if data.stale_by_mtime:
        violations.append(
            Violation(
                rule="TEST011",
                severity=Severity.WARN,
                file="coverage.xml",
                line=0,
                message=(
                    "TEST011: coverage.xml predates a tracked source "
                    "change; TEST005 findings may be stale. Re-run: "
                    "make coverage"
                ),
            )
        )
    if data.module_join_fraction < _TEST011_JOIN_FLOOR:
        violations.append(
            Violation(
                rule="TEST011",
                severity=Severity.WARN,
                file="coverage.xml",
                line=0,
                message=(
                    "TEST011: coverage.xml only covers "
                    f"{data.module_join_fraction:.0%} of known modules -- "
                    "looks deflated (e.g. subprocess coverage not merged); "
                    "TEST005 findings may be false. Re-run: make coverage"
                ),
            )
        )
    return tuple(violations)


# T-0545: the committed coverage-lock path, for TEST012 messages only --
# `frob.gates._coverage` owns the actual path constant and all IO on it.
_COVERAGE_LOCK_REL = "frob-coverage.lock.json"


# frob:ticket T-0545
# frob:tests tests/test_gates.py::TestTestGate.test_test012_missing_lock_warns  # noqa: E501
# frob:tests tests/test_gates.py::TestTestGate.test_test012_drifted_module_warns  # noqa: E501
# frob:tests tests/test_gates.py::TestTestGate.test_test012_matching_lock_is_clean  # noqa: E501
# frob:enforces CHK-GATE-TEST012
def _test012_lock(snapshot: GraphSnapshot, data: CoverageData) -> tuple[Violation, ...]:
    """TEST012 (warn): the committed `frob-coverage.lock.json` (docs/audits/
    gates-accounting.md B5) is missing, or its claimed per-module line
    coverage has drifted from what this run's `coverage.xml` actually shows.

    WARN, not ERROR, for the same reason TEST011 is WARN: this is a new,
    opt-in-by-adoption mechanism (`stamp_coverage` only just started writing
    it, T-0545) and promoting a repo with no lock yet committed straight to
    a hard failure would break every existing checkout on this change
    alone. The severity is intentionally revisited once the lock is
    established as standard practice -- see T-0545's Done report for the
    promotion-to-ERROR follow-up filed for that.
    """
    root = Path(snapshot.root)
    lock = load_coverage_lock(root)
    if lock is None:
        return (
            Violation(
                rule="TEST012",
                severity=Severity.WARN,
                file=str(_COVERAGE_LOCK_REL),
                line=0,
                message=(
                    "TEST012: no committed coverage lock at "
                    f"{_COVERAGE_LOCK_REL} -- TEST005/006's coverage claim "
                    "cannot be verified by a reviewer or CI without trusting "
                    "local .frob/ state; run: frob check --stamp-coverage"
                ),
            ),
        )
    drifted = coverage_lock_diff(lock, data)
    if not drifted:
        return ()
    modules = ", ".join(drifted)
    return (
        Violation(
            rule="TEST012",
            severity=Severity.WARN,
            file=str(_COVERAGE_LOCK_REL),
            line=0,
            message=(
                "TEST012: committed coverage lock diverges from this run's "
                f"coverage.xml for: {modules} -- the committed coverage claim "
                "may not be reproducible from a clean run; re-stamp "
                "(frob check --stamp-coverage) if this run is the accurate one"
            ),
        ),
    )


# T-0997: moved to `frob.gates._coverage` so `stamp_coverage` can call it
# too (the lock-write path needs the SAME filtering this gate-read path
# applies, or TEST012 flags every excluded path as permanent drift -- see
# `_exclude_filtered_coverage`'s docstring there). Re-exported here so this
# module's existing call site and any external importer keep working
# unchanged.
_exclude_filtered_coverage = _coverage_exclude_filtered_coverage


# frob:enforces CHK-GATE-TEST006
def _test006_missing() -> tuple[Violation, ...]:
    """The TEST006 violation for a missing coverage stamp."""
    return (
        Violation(
            rule="TEST006",
            severity=Severity.ERROR,
            file=".frob/coverage-stamp",
            line=0,
            message="TEST006: no coverage stamp found; run: make coverage",
        ),
    )


# frob:ticket T-0403
# frob:tests tests/test_gates.py::TestTestGate.test_test006_stale_on_new_file_not_in_stamp  # noqa: E501
def _test006_stale(
    stamped_hashes: dict, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """TEST006 violation if a stamped file changed OR a source file was added
    since stamping (T-0403 B15: a brand-new file has no entry in
    `stamped_hashes` at all, so it must be treated as stale too, not
    silently skipped -- its coverage is unmeasured by the existing stamp).
    """
    for path, current_hash in snapshot.file_hashes.items():
        if not path.endswith(_SOURCE_EXTS):
            # Coverage stamping only ever hashes _SOURCE_EXTS files
            # (_collect_file_hashes); a doc/.strata/other file the graph
            # also tracks was never in scope for `stamped_hashes` and is
            # not a "new source file" in the coverage sense -- skip it so
            # it is not misreported as staleness.
            continue
        stamped = stamped_hashes.get(path)
        if stamped is None:
            _log.debug("TEST006: coverage stamp missing new file %s", path)
            return (
                Violation(
                    rule="TEST006",
                    severity=Severity.ERROR,
                    file=".frob/coverage-stamp",
                    line=0,
                    message=(
                        f"TEST006: coverage stamp is stale ({path} was added "
                        f"since stamping); run: make coverage"
                    ),
                ),
            )
        if stamped != current_hash:
            _log.debug("TEST006: coverage stamp stale for %s", path)
            return (
                Violation(
                    rule="TEST006",
                    severity=Severity.ERROR,
                    file=".frob/coverage-stamp",
                    line=0,
                    message=(
                        f"TEST006: coverage stamp is stale ({path} changed since "
                        f"stamping); run: make coverage"
                    ),
                ),
            )
    return ()


def _test006(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """TEST006: coverage stamp missing, or stale against current file hashes."""

    root = Path(snapshot.root)
    stamp = load_stamp(root)
    if stamp is None:
        _log.debug("TEST006: no coverage stamp at %s", root)
        return _test006_missing()
    return _test006_stale(stamp.get("file_hashes", {}), snapshot)


# ---------------------------------------------------------------------------
# TEST010
# ---------------------------------------------------------------------------


# frob:waive DUP001 reason="dup grouped this with the sibling per-directive \
# malformed-directive builders -- see _debt001_violations for full reasoning (T-0861)"
# frob:enforces CHK-GATE-TEST010
def _test010_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """TEST010: a `frob:tests` directive's `kind=` attribute is not one of
    unit/integration/e2e (T-0237).

    Mirrors `_waive001_violations`: `frob.graph.dsl` already refuses to turn
    such a line into a TESTS `Edge` at all (an invalid `kind=` degrades the
    directive to a `MalformedDirective`, not silently defaulting), so this
    just surfaces the ones `dsl.py` tagged as `frob:tests`-flavored from
    `GraphSnapshot.malformed` as a real gate violation instead of letting
    them sit as a parse-time warning nobody reads. A `frob:tests` edge's
    CODE-side endpoint not resolving is already caught generically by
    DRIFT002 (`_vanished_endpoint` in `frob.graph.lock` checks every edge's
    `src`/`target`, TESTS edges included -- no TESTS-specific resolver
    needed here, see docs/guides/agent-playbook.md's reuse-the-resolver
    guidance)."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:tests" not in md.reason:
            continue
        _log.debug("TEST010: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="TEST010",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=f"TEST010: {md.file}:{md.line} {md.reason}",
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# TEST013
# ---------------------------------------------------------------------------


# frob:ticket T-0552
# frob:tests tests/test_gates.py::TestTest013NativeUnverified.test_fires_on_structural_only_edge  # noqa: E501
# frob:tests tests/test_gates.py::TestTest013NativeUnverified.test_silent_on_executed_edge  # noqa: E501
# frob:enforces CHK-GATE-TEST013
# frob:enforces CHK-SUBSYS-GATES-ACCOUNTING
# frob:ticket T-1374
def _test013_native_unverified(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """TEST013 (warn): a `frob:tests` edge's TEST001-004 credit rests solely
    on the c/cpp structural fallback (docs/audits/gates-accounting.md
    B3/E3, T-0552; T-0730 retired TS from this fallback -- `collect_ts_
    tests` gives it real vitest execution evidence now) -- frob runs no
    source-accurate ctest collector yet, so the edge was never actually
    executed, only pattern-matched by name/path and confirmed to resolve
    in the graph.

    WARN, not ERROR, and does NOT withdraw the underlying TEST001-004
    credit (see `_edge_is_native_unverified`'s docstring and T-0552's Done
    report for why: withdrawing credit outright, with no real source-
    accurate C/C++ execution collector wired yet, would turn every
    native-language public symbol in every sibling repo's TEST001
    ERROR-red overnight for a structural change alone, not a real
    regression). The point of this
    gate is exactly the audit's alternative fix direction: make the
    degraded-trust state a LOUD, filterable, per-edge finding instead of a
    silent full pass, so a reviewer or `--delta` triage can see precisely
    which "tested" native symbols have zero real execution evidence behind
    them.
    """
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        if not _edge_is_native_unverified(edge, snapshot):
            continue
        violations.append(
            Violation(
                rule="TEST013",
                severity=Severity.WARN,
                file=edge.src.split("::", 1)[0],
                line=0,
                message=(
                    f"TEST013: frob:tests edge {edge.src} -> {edge.target} is "
                    "credited toward TEST001-004 by name/path convention only "
                    "-- frob has no collector that executes it, so this is "
                    "unverified, not proven test coverage"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
def test_gate(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    tests: CollectedTests,
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST001..TEST015. Interfaces derived from packages with public symbols
    (see `_test003`'s docstring for the exact alpha semantics). Coverage is
    consumed as recorded evidence, never produced here. TEST009 (T-0225) is
    `.strata` design files' e2e-binding counterpart to TEST003, which
    `_public_packages` now excludes them from. TEST010 (T-0237) is a
    `frob:tests` directive's own `kind=` attribute failing to parse -- the
    code-endpoint-resolution half of that same ticket needed no new gate
    code at all, since DRIFT002 already covers TESTS edges (see
    `_test010_violations`'s docstring). TEST011 (T-0464, folded into
    `_test005`'s return since it shares the same `coverage.is_nothing`
    guard) is an advisory WARN that coverage.xml itself looks stale or
    deflated, so a spike in TEST005 findings can be triaged as a coverage
    problem rather than a real regression (see `_test011_freshness`).
    TEST012 (T-0545, also folded into `_test005`'s return) is the coverage
    accounting chain's attestability check: the committed
    `frob-coverage.lock.json` summary (`frob.gates._coverage.write_coverage_lock`)
    is missing, or its claimed per-module numbers have drifted from this
    run's `coverage.xml` -- see `_test012_lock`. TEST013 (T-0552, narrowed
    to c/cpp by T-0730) makes the structural-fallback credit `_valid_edges`
    already grants LOUD instead of silent: see `_test013_native_unverified`. TEST014
    (T-0547) is `_inferred_unit_cases`' name-only ambiguity made loud in
    the same spirit: see `_test014_ambiguous_convention`. TEST015 (T-0548)
    is the audit's own B1 repro (`def test_myfunc(): pass` clearing
    TEST001) made loud via T-0549's existing assertion heuristic: see
    `_test015_vacuous_credit`."""
    violations: list[Violation] = []
    violations.extend(_test001_002(snapshot, tests, cfg, coverage))
    violations.extend(_test003(snapshot, tests, cfg))
    violations.extend(_test007_pairs(snapshot, tests, cfg))
    violations.extend(_test004(systems, snapshot, tests))
    violations.extend(_test005(snapshot, systems, coverage, cfg))
    violations.extend(_test006(snapshot))
    violations.extend(_test009(snapshot, tests, cfg))
    violations.extend(_test010_violations(snapshot))
    violations.extend(_test013_native_unverified(snapshot))
    violations.extend(_test014_ambiguous_convention(snapshot, tests))
    violations.extend(_test015_vacuous_credit(snapshot, tests))
    return tuple(violations)


# T-1174: dup_gate/_dup_config/_dup_gate_violations moved to
# frob.gates._dup (DUP001/DUP002/DUP003 family); dup_gate is
# imported at the top of this module and re-exported below.


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this finding traces to an unresolved-callee resolution gap \
# instead (T-1056: leaked Unknown traces to data.get('project', {}).get(field) on a \
# dict already produced by tomllib.load's caught call; plain dict.get access cannot \
# raise)"
def _pyproject_project_field(root: Path, field: str) -> str | None:
    """One `[project].<field>` string from `root/pyproject.toml`, or
    `None` if the file, table, or field is missing/mistyped (extracted
    T-0861): the ONE toml-read-and-key shape `_current_version`
    (`field="version"`) and `_current_project_name` (`field="name"`)
    both need."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    value = data.get("project", {}).get(field)
    return value if isinstance(value, str) else None


def _current_version(root: Path) -> str | None:
    """The project version from pyproject.toml, or None if undetectable."""
    return _pyproject_project_field(root, "version")


# frob:ticket T-0403
# frob:tests tests/test_gates.py::TestTestGate.test_changelog_mentions_rejects_substring_in_prose  # noqa: E501
# frob:tests tests/test_gates.py::TestTestGate.test_changelog_mentions_accepts_real_heading_entry  # noqa: E501
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this finding traces to an unresolved-callee resolution gap \
# instead (T-1056: leaked Unknown traces to pattern.search(text) against a re.Pattern \
# compiled from a version string via re.escape, on text already caught via \
# read_text()'s own OSError handling; a compiled-pattern search over an \
# already-decoded str cannot raise)"
def _changelog_mentions(root: Path, version: str) -> bool:
    """Whether CHANGELOG.md (if present) has a HEADING entry for `version`;
    absent file passes.

    T-0403 B14: a naive substring search matched `version` ANYWHERE in the
    file -- inside an unrelated older entry's prose, a link, or as a prefix
    of a longer number (e.g. "1.2.3" inside "1.2.34") -- so a changelog with
    no real entry for the release could still satisfy REL001. This requires
    the version to appear, bounded by non-digit/non-dot characters, on a
    markdown heading line (`#...`), matching the Keep-a-Changelog
    `## [x.y.z] - ...` convention this repo's own CHANGELOG.md uses.
    """
    pattern = re.compile(r"(?<![0-9.])" + re.escape(version) + r"(?![0-9.])")
    for name in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"):
        path = root / name
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return True
            # frob:waive PERF008 reason="pattern is a compiled re.Pattern built once \
            # just above this loop; .search(line) is a plain regex match with no I/O. \
            # PERF008 resolves the bare method name 'search' by name-only coincidence \
            # to an unrelated same-named function that genuinely reaches walk_pruned \
            # elsewhere in the repo -- a resolver ambiguity, not a real fs-walk on \
            # this call. Tracked as a resolver precision follow-up \
            # (T-1041's Done report)"  # noqa: E501
            return any(
                line.lstrip().startswith("#") and pattern.search(line)
                for line in text.splitlines()
            )
    return True


def _rel001_version(manifest, snapshot, current_version):  # noqa: ANN001
    """REL001 for an under-bumped version, plus the computed bump class."""
    from frob.release import diff_class, required_version, satisfies

    bump = diff_class(manifest, snapshot)
    need = required_version(manifest.version, bump)
    if need.is_ok and not satisfies(current_version, need.danger_ok):
        cls = bump.name.lower()
        return bump, [
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file="pyproject.toml",
                line=0,
                message=(
                    f"REL001: public API changed ({cls}) since {manifest.version}; "
                    f"bump the version to >= {need.danger_ok} (currently "
                    f"{current_version}), then run: frob release stamp"
                ),
            )
        ]
    return bump, []


# frob:ticket T-0731
# frob:tests tests/test_gates.py::TestDebtGate.test_release_gate_bump_suppressed_under_frob_agent  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_release_gate_bump_fires_without_frob_agent  # noqa: E501
def _rel001_bump_suppressed_under_agent() -> bool:
    """T-0731: whether the bump/changelog half of REL001 is suppressed
    because `FROB_AGENT` (T-0574) names this an explicitly-flagged agent
    shell.

    Version bump and changelog authorship are land-time steps owned
    exclusively by `frob ticket land` (T-0731) -- agents must never
    touch `pyproject.toml`'s version, `uv.lock`, or `CHANGELOG.md`
    themselves. This is the explicit-env-var override T-0807 preserves
    alongside its own context-derived detection (`_rel001_land_owned`)
    below -- a shell that sets `FROB_AGENT` by hand still gets the same
    suppression it always has, with no worktree/lease evidence required.
    """
    # frob:waive SEC110 reason="worktree-agent detection flag, not a secret"
    return bool(os.environ.get("FROB_AGENT"))


# frob:ticket T-0807
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_linked_worktree_detected  # noqa: E501
def _rel001_is_linked_worktree(root: Path) -> bool:
    """T-0807: whether `root` is a LINKED git worktree (as opposed to the
    repo's main/root checkout) -- `git rev-parse --git-dir` resolves to a
    worktree-private path (`.git/worktrees/<name>`) that differs from
    `--git-common-dir` (the shared `.git` every worktree of the clone
    points back at) exactly when `root` is a linked worktree; in the main
    checkout the two spawns resolve to the same path. Degrades to `False`
    (no suppression) on any git failure -- a plain, non-worktree checkout
    is the default REL001 posture this must never silently change.
    """
    git_dir_spawned = run_argv(("git", "-C", str(root), "rev-parse", "--git-dir"))
    common_dir_spawned = run_argv(
        ("git", "-C", str(root), "rev-parse", "--git-common-dir")
    )
    if git_dir_spawned.is_err or common_dir_spawned.is_err:
        return False
    git_dir_result = git_dir_spawned.danger_ok
    common_dir_result = common_dir_spawned.danger_ok
    if git_dir_result.returncode != 0 or common_dir_result.returncode != 0:
        return False
    git_dir = Path(git_dir_result.stdout.strip())
    common_dir = Path(common_dir_result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    return git_dir != common_dir


# frob:ticket T-0807
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_ticket_lease  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_linked_worktree_no_ticket  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_not_land_owned_root_checkout_no_ticket  # noqa: E501
def _rel001_land_owned(root: Path, ticket_id: str | None) -> bool:
    """T-0807: whether REL001's bump/changelog half is land-owned in THIS
    check run, derived from CONTEXT rather than the `FROB_AGENT` env var
    reviewers and some dispatch shells never set (the recurring-friction
    report this ticket exists to fix -- 4+ review cycles hand-rejected a
    bump `frob ticket land` auto-cleared seconds later).

    Land-owned whenever EITHER holds:

    - `ticket_id` is set and its cross-worktree lease (`resolve_lease`,
      T-0766) pins to `root` -- an in-progress ticket in its own worktree
      is definitionally pre-land.
    - `root` itself is a linked worktree (`_rel001_is_linked_worktree`),
      regardless of ticket id -- a linked worktree is never where a
      release gets cut, ticket context or not.

    A plain root-checkout run with no `--ticket` and no live lease is
    NOT land-owned -- REL001 errors exactly as before T-0807 there,
    which is the explicit "keep the plain no-ticket behavior erroring"
    acceptance case. `_rel001_bump_suppressed_under_agent`'s explicit
    `FROB_AGENT` override is checked separately by the caller and is
    unaffected by this function's result.
    """
    from frob.tickets._leases import resolve_lease

    if ticket_id is not None:
        lease_result = resolve_lease(root, ticket_id, root)
        if lease_result.is_ok:
            _log.debug(
                "release_gate: %s lease pins to %s -- land-owned via ticket lease",
                ticket_id,
                root,
            )
            return True
    if _rel001_is_linked_worktree(root):
        _log.debug("release_gate: %s is a linked worktree -- land-owned", root)
        return True
    return False


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0003
# frob:ticket T-0807
def release_gate(
    root: Path, snapshot: GraphSnapshot, ticket_id: str | None = None
) -> tuple[Violation, ...]:
    """REL001: the public-API change since the last `frob release stamp`
    demands a version bump the declared version does not cover, or the
    changelog does not mention the version.

    Opt-in: runs only when a `.frob-release.json` manifest exists. The
    version-bump/changelog half is suppressed whenever it is LAND-OWNED
    (T-0807): either the explicit `FROB_AGENT` env-var override (T-0731,
    `_rel001_bump_suppressed_under_agent`), or context derived from
    `ticket_id`/`root` (`_rel001_land_owned` -- a live worktree lease for
    `ticket_id`, or `root` itself being a linked worktree). A land-owned
    run that WOULD have needed a bump still reports it, downgraded to an
    informational `WARN` rather than an `ERROR` (`_rel001_land_note`) --
    version bump is a land-time step owned by `frob ticket land`, not
    something a worktree agent or reviewer does, but the API-diff signal
    itself stays visible. A plain root checkout with no ticket and no
    lease keeps erroring exactly as before T-0807.
    """
    from frob.release import load_manifest

    root = Path(root)
    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.debug("release_gate: no manifest, skipping")
        return ()

    current_version = _current_version(root)
    if current_version is None:
        _log.debug("release_gate: no detectable project version, skipping")
        return ()

    if _rel001_bump_suppressed_under_agent():
        # T-0731's explicit `FROB_AGENT` override: full legacy silence, no
        # informational note either -- an agent shell that opts in by hand
        # gets exactly the pre-T-0807 behavior, unchanged.
        from frob.release import diff_class

        _log.info(
            "release_gate: REL001 bump/changelog suppressed under FROB_AGENT "
            "(T-0731) -- version bump is a land-time step"
        )
        bump, violations = diff_class(manifest_result.danger_ok, snapshot), []
    elif _rel001_land_owned(root, ticket_id):
        from frob.release import diff_class

        _log.info(
            "release_gate: REL001 bump/changelog demand land-owned (T-0807) "
            "-- reporting the API diff as an informational note, not an error"
        )
        bump = diff_class(manifest_result.danger_ok, snapshot)
        violations = _rel001_land_note(bump, manifest_result.danger_ok, current_version)
    else:
        bump, violations = _rel001_version(
            manifest_result.danger_ok, snapshot, current_version
        )
        if bump != 0 and not _changelog_mentions(root, current_version):
            violations.append(_rel001_missing_changelog(current_version))
    # T-0412: a release must never ship with ANY open frob:debt, expired or
    # not -- debt is collected and re-raised before shipping, never
    # silently carried forward as a de facto permanent waiver.
    violations.extend(_release_open_debt_violations(snapshot))
    # T-0576: unlike debt, a release only refuses to ship over an EXPIRED
    # deprecation -- one still inside its warning window is fine.
    violations.extend(
        _release_expired_deprecated_violations(
            snapshot, current_date=date.today().isoformat()
        )
    )
    # T-1009: REL002 -- .frob-release.json is the ONE version authority;
    # every derived artifact (pyproject.toml/uv.lock/CHANGELOG.md) must
    # agree with it at all times, independent of REL001's land-owned/
    # FROB_AGENT bump suppression above -- a hand-edit that desyncs an
    # artifact is a bug the instant it happens, not just at land time.
    violations.extend(_rel002_coherence_violations(root, manifest_result.danger_ok))
    _log.info("release_gate: bump=%s, %d violation(s)", bump.name, len(violations))
    return tuple(violations)


# frob:ticket T-1009
def _current_project_name(root: Path) -> str | None:
    """The project name from `pyproject.toml`'s `[project].name`, or
    `None` if undetectable (T-1009 -- `_uv_lock_version`'s key into
    `uv.lock`'s `[[package]]` table)."""
    return _pyproject_project_field(root, "name")


# frob:ticket T-1009
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this finding traces to an unresolved-callee resolution gap \
# instead (T-1056: leaked Unknown traces to data.get('package', []) iteration and \
# package.get(...) dict access on a dict already produced by tomllib.load's caught \
# call; plain dict/list access cannot raise)"
def _uv_lock_version(root: Path) -> str | None:
    """The project's own package `version` as recorded in `root/uv.lock`'s
    `[[package]]` table (matched by `pyproject.toml`'s `[project].name`),
    or `None` if the file is absent/unparsable/has no matching entry
    (T-1009)."""
    name = _current_project_name(root)
    if name is None:
        return None
    path = root / "uv.lock"
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    for package in data.get("package", []):
        if package.get("name") == name:
            version = package.get("version")
            return version if isinstance(version, str) else None
    return None


# frob:ticket T-1009
# frob:invariant INV-044
# invariant spec: [INV-044](invariants/INV-044.md)
# frob:tests tests/test_release.py::TestReleaseGateCoherence.test_hand_edited_pyproject_fires_rel002  # noqa: E501
# frob:enforces CHK-GATE-REL002
def _rel002_coherence_violations(root: Path, manifest) -> list[Violation]:  # noqa: ANN001
    """REL002 (T-1009): `.frob-release.json`'s `version` is the ONE version
    authority; `pyproject.toml`, `uv.lock`, and CHANGELOG.md are derived
    artifacts regenerated from it by `frob release sync`. Any artifact that
    disagrees is named in a single ERROR-severity finding -- born ERROR
    (DOC007 precedent, T-0986): a repo that has actually run `sync` has
    zero disagreements, so this never fires on a clean tree."""
    authoritative = manifest.version
    disagreements: list[str] = []

    pyproject_version = _current_version(root)
    if pyproject_version is not None and pyproject_version != authoritative:
        disagreements.append(f"pyproject.toml (version={pyproject_version})")

    lock_version = _uv_lock_version(root)
    if lock_version is not None and lock_version != authoritative:
        disagreements.append(f"uv.lock (version={lock_version})")

    if not disagreements:
        return []
    return [
        Violation(
            rule="REL002",
            severity=Severity.ERROR,
            file=".frob-release.json",
            line=0,
            message=(
                f"REL002: .frob-release.json is the version authority "
                f"({authoritative}), but disagrees with: "
                f"{', '.join(disagreements)} -- run `frob release sync`"
            ),
        )
    ]


# frob:ticket T-0807
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_linked_worktree_no_ticket  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_ticket_lease  # noqa: E501
def _rel001_land_note(bump, manifest, current_version: str) -> list[Violation]:  # noqa: ANN001
    """REL001, land-owned case (T-0807): a `WARN`-severity note naming the
    API-diff `bump` class AND the target version (mirroring `_rel001_version`'s
    `required_version` computation, T-0894 review fix) when a real bump would
    otherwise be demanded, so a reviewer still SEES both the diff and what
    `frob ticket land` will bump to ("public API changed (minor) since X;
    land-owned -- frob ticket land will bump to >= Y") without the review
    being blocked by a bump `frob ticket land` computes and applies itself
    seconds later. `[]` when `bump` is the no-op class, or when the required
    version cannot be computed -- nothing changed (or nothing computable),
    nothing to note."""
    from frob.release import required_version

    if bump == 0:
        return []
    need = required_version(manifest.version, bump)
    if need.is_err:
        return []
    cls = bump.name.lower()
    return [
        Violation(
            rule="REL001",
            severity=Severity.WARN,
            file="pyproject.toml",
            line=0,
            message=(
                f"REL001: public API changed ({cls}) since {manifest.version}; "
                f"land-owned -- frob ticket land will bump to >= {need.danger_ok}"
            ),
        )
    ]


def _rel001_missing_changelog(current_version: str) -> Violation:
    """REL001: the public API changed but CHANGELOG.md has no entry for
    `current_version`."""
    return Violation(
        rule="REL001",
        severity=Severity.ERROR,
        file="CHANGELOG.md",
        line=0,
        message=(
            f"REL001: no CHANGELOG.md entry for {current_version}; the "
            f"public API changed and needs a release note"
        ),
    )


# T-1183: _fuzz_enforce/fuzz_gate/_fuzz_gate_violations moved to
# frob.gates._fuzz (FUZZ001/FUZZ002/FUZZ003 family); fuzz_gate is
# imported at the top of this module and re-exported below.


def _perf_gate_candidate_paths(snapshot: GraphSnapshot) -> list[str]:
    """Every `snapshot.file_hashes` path with a registered tree-sitter
    grammar (`frob.lang.tree_sitter_extensions`, the canonical T-0129
    extension table -- not a hand-copied duplicate); files with no
    registered grammar are unscannable by design and are filtered out here
    so they never reach `parse_file` and never produce an
    UnsupportedLanguage skip line (T-0203)."""
    from frob.lang import tree_sitter_extensions

    scannable_extensions = tree_sitter_extensions()
    ordered_paths = sorted(snapshot.file_hashes)
    candidate_paths = [
        rel_path
        for rel_path in ordered_paths
        if Path(rel_path).suffix.lower() in scannable_extensions
    ]
    skipped_unscannable = len(ordered_paths) - len(candidate_paths)
    if skipped_unscannable:
        _log.debug(
            "perf_gate: %d file(s) filtered out (no registered grammar)",
            skipped_unscannable,
        )
    return candidate_paths


# frob:doc docs/modules/perf.md#integration-points
# frob:ticket T-0021
# frob:ticket T-0203
def perf_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PERF001..PERF008 (`frob.perf.perf_rules`) plus PERF009 (T-0712's
    regression ratchet, `frob.perf._ratchet.ratchet_violations`), run at
    the policy/gates stage per docs/modules/perf.md's Integration points.
    Parses every scannable source file (see `_perf_gate_candidate_paths`)
    and hands the parsed set to `frob.perf.perf_rules` (same posture as
    `frob.policy`'s `_pattern_violations`: gates does the IO, `perf_rules`
    stays pure). A file whose extension SHOULD parse but fails still gets
    a visible skip message. PERF009 is read straight from
    `.frob/perf/ratchet_findings.json` (a `frob perf collect` artifact,
    never a live re-collection at gate time)."""
    from frob.perf import perf_rules
    from frob.perf._ratchet import ratchet_violations

    candidate_paths = _perf_gate_candidate_paths(snapshot)
    parsed = _perf_gate_parse_files(root, candidate_paths)
    violations = list(perf_rules(snapshot, parsed))
    violations.extend(ratchet_violations(root))
    _log.info(
        "perf_gate: %d file(s) scanned, %d violation(s)", len(parsed), len(violations)
    )
    return tuple(violations)


def _perf_gate_parse_files(root: Path, candidate_paths: list[str]) -> list[ParsedFile]:
    """Parse every scannable candidate path, skipping (with a logged
    warning) any that fails to parse."""
    from frob.lang import parse_file

    parsed: list[ParsedFile] = []
    for rel_path in candidate_paths:
        result = parse_file(root / rel_path)
        if result.is_err:
            _log.warning(
                "perf_gate: skipping unparsed %s: %s", rel_path, result.danger_err
            )
            continue
        parsed.append(result.danger_ok)
    return parsed


_CACHE_REL = Path(".frob") / "cache.db"

# frob:ticket T-1340
_ALL_GATES = frozenset(
    {
        "drift",
        "coverage",
        "scope",
        "prework",
        "invariant",
        "test",
        "policy",
        "doclink",
        "docanchor",
        "docstatus",
        "docmake",
        "perf",
        "fuzz",
        "release",
        "clones",
        "decisions",
        "sys",
        "secrets",
        "tickets",
        "archgate",
        # T-0665: OPAQUE001, fail-closed runtime-resolved capability-
        # indirection obligation (frob.gates._opaque.opaque_gate).
        "opaque",
        "pii_structural",
        "refs",
        "registry",
        "docblocks",
        "walk_lint",
        "excludehazard",
        # T-0412: frob:debt malformed/non-open-ticket/expired-until checks.
        "debt",
        # T-0459: bare stdout write outside frob.render.
        "render_lint",
        # T-0558: PARSE001, a swallowed frob.lang parse/IO failure.
        "parse_failures",
        # T-0422: DEAD001, an unreferenced private symbol.
        "dead_symbols",
        # T-1428: WIRE001/WIRE002, a ticket's own diff adding code nothing
        # outside its own tests can reach.
        "wire",
        # T-0405: LANG001, language-extension conformance drift-lock.
        "lang_conformance",
        # T-0406: LANG002/LANG003, per-project language conformance.
        "lang_project_conformance",
        # frob:ticket T-0797
        # T-0576/T-0797: DEPR001-004, frob:deprecated lifecycle checks --
        # implemented since T-0576 but never registered here, so no real
        # `frob check` run ever evaluated them (catalogued-is-not-enforced).
        "deprecated",
        # T-0813: PROTO001, the production compute_protocol_summaries
        # entrypoint (frob.gates._protocol_summary).
        "protocol_summary",
        # T-0788: COMPLIANCE005, dispatching frob.strata._compliance's
        # check_cmpl_registry (built by T-0607, wired here).
        "compliance",
        # T-0851: FMT001, the T-0441 follow-up (frob.gates.fmt_gate).
        "fmt",
        # T-0628: AFFECT001/AFFECT002, the T-0325 affects()-closure
        # digest-drift enforcement half (frob.gates.affect_drift_gate).
        "affect_drift",
        # T-0688: EXHAUST001/EXHAUST002, the exhaustive-exception gate
        # over frob.arch._mayraise.compute_may_raise's per-function sets
        # (frob.gates._exhaustive_handling.exhaustive_handling_gate).
        "exhaustive_handling",
        # T-0690: FFI001/FFI002, the FFI-boundary exception-declaration
        # cross-check (frob.gates._ffi_boundary.ffi_boundary_gate).
        "ffi_boundary",
        # T-1340: SUPPRESS001, evidence-driven suppression-dialect
        # mismatch detection (frob.gates._suppress.suppress001_gate).
        "suppress",
    }
)


@dataclass(frozen=True)
class _GateInputs:
    """All loaded state the pure gates consume, assembled once by `run_gates`.

    `root` is the (possibly scoped) path `cfg.root` names -- it filters which
    files a gate scans/reports on. `repo_root` (T-0314) is always the git/frob
    root regardless of scoping: any directive whose target is a repo-relative
    path (e.g. a `frob:doc docs/x.md#anchor` target file) must resolve against
    `repo_root`, never `root` -- a scoped `frob check <subdir>` run must not
    rebase repo-relative path text just because the scanned set shrank.
    """

    root: Path
    repo_root: Path
    cfg: GateConfig
    snapshot: GraphSnapshot
    queue: TicketQueue
    lock: LockFile
    diff: Diff
    tests: CollectedTests
    invariants: tuple[Invariant, ...]
    rules: tuple
    rule_ids: frozenset[str]
    coverage: Option[CoverageData]
    test_policy: TestPolicy
    systems: tuple[SystemSpec, ...]
    ticket: Ticket | None = None
    sweep: Option[PreworkSweep] = field(default_factory=Nothing)
    # frob:ticket T-0550
    diff_load_failed: bool = False
    # frob:ticket T-0719
    diff_load_no_repo: bool = False
    # frob:ticket T-1161
    python_collection_failed: str | None = None


# frob:ticket T-0550
# frob:ticket T-0719
def _load_diff(root: Path, base: str) -> tuple[Diff, bool, bool]:
    """The working diff against `base`, degrading to an empty diff on failure,
    plus whether that degrade happened at all, plus whether it happened
    because `root` is not inside a git repository in the first place.

    A missing diff (fresh repo, unknown base, detached HEAD) must not skip the
    whole gates stage -- only coverage/scope/TODO001 read it, so the
    diff-dependent gates simply see no touched symbols. But "no touched
    symbols" is ALSO exactly what a genuinely clean diff (nothing changed)
    looks like, so a caller that only sees the empty `Diff` cannot tell a
    real failure (bad `--base`, no merge-base, git error) apart from a
    legitimately quiet tree -- and COV002/SCOPE001/TODO001 all treat "no
    touched symbols" as "nothing to enforce", silently passing on a failure
    that should instead be a loud blocking condition (T-0550/B8). The second
    element of the returned tuple is that distinguishing signal: `True`
    means `working_diff` itself errored and the `Diff` returned is a
    placeholder, never a real one.

    T-0719: within that "diff genuinely failed" bucket, a genuinely
    git-less `root` (a plain filesystem directory, no `.git` anywhere above
    it -- e.g. a system-test fixture that never calls `git init`) is a
    DIFFERENT failure shape than a real repo's bad `--base`/detached-HEAD
    working_diff failure -- `working_diff`'s own `GitError` does not
    distinguish the two (`_merge_base` collapses both to
    `GitError.GitFailed`), but `repo_root` does (`NotARepo` specifically).
    The third element of the returned tuple carries that finer signal:
    `True` only when `root` is not inside a git repository at all. Callers
    that want T-0550/B8's original "a real repo's diff failed" protection
    to keep firing exactly as before (PRE001's `no_ticket_blocks`) should
    keep branching on the second element alone; callers that should treat
    a no-repo-at-all root the same as a clean/empty diff (COV002/SCOPE001/
    TODO001, per this ticket) branch on `diff_load_failed and not
    diff_load_no_repo` instead.
    """
    no_repo = _git_repo_root(root).is_err
    diff_result = working_diff(root, base)
    if diff_result.is_err:
        if no_repo:
            _log.debug(
                "run_gates: %s is not inside a git repository; COV002/"
                "SCOPE001/TODO001 see an empty diff, not a diff-load failure",
                root,
            )
        else:
            _log.warning(
                "run_gates: working_diff failed (%s); diff-dependent gates "
                "see no touched set",
                diff_result.danger_err,
            )
        return Diff(base=base, hunks=()), True, no_repo
    return diff_result.danger_ok, False, False


def _load_tests(root: Path) -> tuple[CollectedTests, str | None]:
    """Collected pytest + cargo + vitest + ctest node ids, degrading each
    collector independently to an empty set on failure (a missing/broken
    toolchain must not halt the whole gates run -- but see `_cov003`: an
    evidence id that consequently fails to resolve becomes a loud
    violation, never a silent pass, T-0102). T-0730 adds `collect_ts_tests`
    (vitest) and `collect_cpp_tests` (ctest) alongside the pre-existing
    python/rust collectors (T-0587 built the collectors; this is where
    `frob.gates` starts actually consuming their node ids).

    T-1161: also returns the python collector's failure detail (`frob.
    testing.python_collection_failure_detail()`, `None` when python
    collection succeeded) alongside the merged `CollectedTests` -- `run_gates`
    threads this into `coverage_gate` so a total pytest-collection failure
    reports as ONE honest `COV003` instead of one per archived evidence id."""
    node_ids: set[str] = set()

    python_result = collect_python_tests(root)
    python_collection_failed: str | None = None
    if python_result.is_err:
        _log.error("run_gates: pytest collection failed: %s", python_result.danger_err)
        python_collection_failed = (
            python_collection_failure_detail()
            or f"collect_python_tests failed: {python_result.danger_err}"
        )
    else:
        node_ids.update(python_result.danger_ok.node_ids)

    rust_result = collect_rust_tests(root)
    if rust_result.is_err:
        _log.error("run_gates: cargo collection failed: %s", rust_result.danger_err)
    else:
        node_ids.update(rust_result.danger_ok.node_ids)

    ts_result = collect_ts_tests(root)
    if ts_result.is_err:
        _log.error("run_gates: vitest collection failed: %s", ts_result.danger_err)
    else:
        node_ids.update(ts_result.danger_ok.node_ids)

    cpp_result = collect_cpp_tests(root)
    if cpp_result.is_err:
        _log.error("run_gates: ctest collection failed: %s", cpp_result.danger_err)
    else:
        node_ids.update(cpp_result.danger_ok.node_ids)

    return CollectedTests(node_ids=frozenset(node_ids)), python_collection_failed


def _resolve_ticket(
    root: Path, cfg: GateConfig, queue: TicketQueue
) -> tuple[Ticket | None, Option[PreworkSweep]]:
    """The active ticket (if any) and its recorded pre-work sweep."""
    ticket_id_opt = active_ticket(root, cfg.ticket)
    if ticket_id_opt.is_nothing:
        return None, Nothing()
    ticket = queue.tickets.get(ticket_id_opt.danger_some)
    if ticket is None:
        _log.warning(
            "run_gates: active ticket %s not in queue", ticket_id_opt.danger_some
        )
        return None, Nothing()
    loaded_sweep = load_prework(root, ticket.id)
    sweep: Option[PreworkSweep] = (
        Some(loaded_sweep) if loaded_sweep is not None else Nothing()
    )
    return ticket, sweep


_T = TypeVar("_T")
_E = TypeVar("_E")


def _require(
    result: Result[_T, _E], step: str, err: GateError
) -> Result[_T, GateError]:
    """Log+map one `_load_required_state` step's failure to `err`, or pass
    its `danger_ok` value through unchanged, preserving `result`'s Ok type."""
    if result.is_err:
        _log.error("run_gates: %s failed: %s", step, result.danger_err)
        return Err(err)
    return Ok(result.danger_ok)


def _load_graph_queue_lock(
    root: Path,
) -> Result[tuple[GraphSnapshot, TicketQueue, LockFile], GateError]:
    """Load the graph snapshot, ticket queue, and lock file -- the first
    third of `_load_required_state`'s mandatory loads."""
    build = _require(
        build_graph(root, root / _CACHE_REL), "graph build", GateError.GraphUnavailable
    )
    if build.is_err:
        return Err(build.danger_err)
    queue = _require(load_queue(root), "ticket queue load", GateError.QueueUnavailable)
    if queue.is_err:
        return Err(queue.danger_err)
    lock = _require(
        load_lock(root / "frob.lock"), "lock load", GateError.ConfigMalformed
    )
    if lock.is_err:
        return Err(lock.danger_err)
    return Ok((build.danger_ok, queue.danger_ok, lock.danger_ok))


def _load_required_state(
    root: Path,
) -> Result[
    tuple[GraphSnapshot, TicketQueue, LockFile, tuple[Invariant, ...], list], GateError
]:
    """Load the gates' mandatory state -- graph, ticket queue, lock,
    invariants, policy -- or the first hard failure."""
    from frob.policy import load_policy

    first = _load_graph_queue_lock(root)
    if first.is_err:
        return Err(first.danger_err)
    build_ok, queue_ok, lock_ok = first.danger_ok

    invariants = _require(
        load_invariants(root), "invariants load", GateError.ConfigMalformed
    )
    if invariants.is_err:
        return Err(invariants.danger_err)
    policy = _require(load_policy(root), "policy load", GateError.ConfigMalformed)
    if policy.is_err:
        return Err(policy.danger_err)
    return Ok(
        (build_ok, queue_ok, lock_ok, invariants.danger_ok, list(policy.danger_ok))
    )


def _repo_root_for(root: Path) -> Path:
    """The git/frob root for `root` (T-0314): `frob.gitio.repo_root`, falling
    back to `root` itself when `root` is not inside a git repo (e.g. a
    synthetic test fixture) so callers always get a usable path, never a
    Result to unwrap."""
    from frob.gitio import repo_root as git_repo_root

    result = git_repo_root(root)
    if result.is_err:
        _log.debug(
            "run_gates: repo_root(%s) unavailable (%s); falling back to root itself",
            root,
            result.danger_err,
        )
        return root
    return result.danger_ok


def _assemble_gate_inputs(root: Path, cfg: GateConfig, required: tuple) -> _GateInputs:
    """Build the full `_GateInputs` from `_load_required_state`'s mandatory
    state plus the remaining optional/derived loads (coverage, test policy,
    active ticket)."""
    snapshot, queue, lock, invariants, rules = required
    coverage_result = load_coverage(root, snapshot)
    coverage: Option[CoverageData] = (
        Some(coverage_result.danger_ok) if coverage_result.is_ok else Nothing()
    )
    test_policy, systems = _load_test_config(root)
    ticket, sweep = _resolve_ticket(root, cfg, queue)
    diff, diff_load_failed, diff_load_no_repo = _load_diff(root, cfg.base)
    tests, python_collection_failed = _load_tests(root)
    return _GateInputs(
        root=root,
        repo_root=_repo_root_for(root),
        cfg=cfg,
        snapshot=snapshot,
        queue=queue,
        lock=lock,
        diff=diff,
        tests=tests,
        invariants=invariants,
        rules=tuple(rules),
        rule_ids=frozenset(r.id for r in rules),
        coverage=coverage,
        test_policy=test_policy,
        systems=systems,
        ticket=ticket,
        sweep=sweep,
        diff_load_failed=diff_load_failed,
        diff_load_no_repo=diff_load_no_repo,
        python_collection_failed=python_collection_failed,
    )


def _load_inputs(cfg: GateConfig) -> Result[_GateInputs, GateError]:
    """Load every piece of state the gates need, or the first hard failure."""
    root = Path(cfg.root)
    required = _load_required_state(root)
    if required.is_err:
        return Err(required.danger_err)
    return Ok(_assemble_gate_inputs(root, cfg, required.danger_ok))


# frob:ticket T-0415
# T-0415 (docs/audits/perf.md H3): these gates are pure-Python, CPU-bound,
# and (per the audit's measured wall-time) the largest jobs in the run --
# sharing one ThreadPoolExecutor with everything else means the GIL
# serializes them instead of letting them overlap (archgate 91.5s + sys
# 77s summed, not maxed). They run in a ProcessPoolExecutor instead, where
# each gets its own interpreter and genuinely overlaps the others. Every
# other gate is I/O-bound or cheap enough that process-spawn/pickle
# overhead would not pay for itself, so it stays on the thread pool.
_PROCESS_POOL_GATES: frozenset[str] = frozenset(
    {
        "archgate",
        "sys",
        "clones",
        "perf",
        "pii_structural",
        "secrets",
        "dead_symbols",
        "wire",
        "protocol_summary",
    }
)

# frob:ticket T-0415
# The exact gate-name order `_build_jobs` used to assemble its single dict
# in, before the CPU-bound subset moved to a second (process) pool. Merging
# thread-pool and process-pool results back into this fixed order (T-0415)
# is what keeps `frob check` output byte-identical to the old single-pool
# run regardless of which pool a given job actually finishes in first --
# real concurrency changes wall time, never violation order.
_CANONICAL_GATE_ORDER: tuple[str, ...] = (
    "drift",
    "coverage",
    "invariant",
    "test",
    "policy",
    "doclink",
    "docanchor",
    "docstatus",
    "docmake",
    "perf",
    "fuzz",
    "release",
    "clones",
    "decisions",
    "sys",
    "secrets",
    # T-0665: OPAQUE001.
    "opaque",
    "tickets",
    "archgate",
    "pii_structural",
    "refs",
    "registry",
    "docblocks",
    "walk_lint",
    "excludehazard",
    "debt",
    # frob:ticket T-0797
    "deprecated",
    "render_lint",
    "parse_failures",
    "dead_symbols",
    # frob:ticket T-1428
    "wire",
    # frob:ticket T-0813
    "protocol_summary",
    # frob:ticket T-0788
    "compliance",
    "lang_conformance",
    "lang_project_conformance",
    "scope",
    "prework",
    # frob:ticket T-0851
    "fmt",
    # frob:ticket T-0628
    "affect_drift",
    # frob:ticket T-0688
    "exhaustive_handling",
    # frob:ticket T-0690
    "ffi_boundary",
    # frob:ticket T-1340
    "suppress",
)

# T-0839: import-time guard making the two constants' drift impossible to
# ship, not just catchable at runtime -- `TestGateOrderSetEquality`
# (tests/test_gates.py) is the same check exercised as a test, but this
# assertion fires the instant the module is imported (any `frob` process),
# not only when the test suite happens to run.
assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES, (
    "_CANONICAL_GATE_ORDER and _ALL_GATES have drifted apart -- every gate "
    "in _ALL_GATES must appear exactly once in _CANONICAL_GATE_ORDER so "
    "merge order stays deterministic and no gate silently drops from "
    "frob check output"
)
assert len(_CANONICAL_GATE_ORDER) == len(set(_CANONICAL_GATE_ORDER)), (
    "_CANONICAL_GATE_ORDER contains a duplicate gate name"
)


# frob:ticket T-0415
@dataclass(frozen=True)
class _ProcessJob:
    """One CPU-bound gate job dispatched to the process pool (T-0415): a
    module-level, picklable-by-reference gate function plus its picklable
    positional args (`Path`/frozen pydantic models only -- no closures, no
    native/Rust handles), so `ProcessPoolExecutor.submit` can ship it to a
    worker without touching a lambda."""

    func: Callable[..., tuple[Violation, ...]]
    args: tuple


# frob:ticket T-0415
# frob:ticket T-0602
# T-0602: the closed, hand-audited allowlist `_gate_cache.evaluate_
# cacheable_gate` is permitted to serve from `.frob/gate-cache.db` instead
# of re-running for real. A gate qualifies only if its ENTIRE thread-pool
# closure body (see the matching case in `_build_jobs` below) reads
# `st.snapshot` (via the tracked `TrackedSnapshot` proxy, so every file it
# touches is observed) plus, at most, a short tuple of already-hashable
# scalars folded in through `extra` -- never `st.root`/`st.repo_root`
# (an unbounded, untracked filesystem walk) and never a gate whose single
# dispatch name secretly bundles a root-scanning sub-check alongside a
# snapshot-only one (e.g. "invariant", "docblocks" -- excluded for exactly
# this reason). See `_gate_cache`'s module docstring for the full
# reasoning and `docs/modules/serve.md`'s "What it does NOT cover" section
# for the gates this EXCLUDES and why, disclosed rather than silently
# assumed safe.
# T-0639 (post-T-0602 landing): "deprecated" gained a `root: Path` argument
# (DEPR005's baseline-lock/live-reference-set resolution, filesystem-
# dependent beyond the snapshot) -- removed from this allowlist rather than
# cached unsoundly; see the exclusion note above.
_CACHEABLE_GATES: frozenset[str] = frozenset(
    {
        "drift",
        "test",
        "policy",
        "parse_failures",
        "debt",
        "lang_conformance",
        "affect_drift",
    }
)


# frob:ticket T-1454
def _cacheable_gate_factories(
    st: _GateInputs, current_date: str
) -> dict[
    str, tuple[Callable[[GraphSnapshot], tuple[Violation, ...]], tuple[str, ...]]
]:
    """Per-`_CACHEABLE_GATES`-member table of `(call, extra_key)` factories,
    extracted from `_cacheable_gate_call` (T-1454) to keep that function
    under the ARCH001 line budget: one dict literal, built fresh per call
    since each entry closes over `st`/`current_date`, rather than a chain
    of `if name == ...: return ...` branches. Every entry's SIDE-INPUT key
    discipline (T-1454's `model_side_channel_key` folding) is unchanged --
    only the dispatch shape moved."""
    from frob.policy import policy_gate

    current_version = _current_version(st.repo_root) or "0.0.0"
    return {
        "drift": (
            lambda snap: drift_gate(snap, st.lock),
            (model_side_channel_key(st.lock),),
        ),
        "test": (
            lambda snap: test_gate(
                snap, st.systems, st.coverage, st.tests, st.test_policy
            ),
            (
                model_side_channel_key(
                    st.systems, st.coverage, st.tests, st.test_policy
                ),
            ),
        ),
        "policy": (
            lambda snap: policy_gate(st.rules, snap, st.diff),
            (model_side_channel_key(st.rules, st.diff),),
        ),
        "parse_failures": (lambda snap: parse_failure_gate(snap), ()),
        "debt": (
            lambda snap: debt_gate(
                snap,
                st.queue,
                current_date=current_date,
                current_version=current_version,
            ),
            (current_date, current_version, model_side_channel_key(st.queue)),
        ),
        "lang_conformance": (lambda _snap: lang_conformance_gate(), ()),
        "affect_drift": (
            lambda snap: affect_drift_gate(snap, st.diff),
            (model_side_channel_key(st.diff),),
        ),
    }


# frob:ticket T-1454
def _cacheable_gate_call(
    name: str, st: _GateInputs
) -> tuple[Callable[[GraphSnapshot], tuple[Violation, ...]], tuple[str, ...]]:
    """The pure `(snapshot) -> violations` call for one `_CACHEABLE_GATES`
    member, plus its `extra` scalar key inputs -- kept in exact lockstep
    with the matching (non-cached) closure body in `_build_jobs` below by
    construction: both read from the same `st`, this one just takes
    `snapshot` as an explicit argument instead of closing over `st.snapshot`
    directly, so `_gate_cache.evaluate_cacheable_gate` can substitute a
    `TrackedSnapshot` in its place.

    T-1454: every gate here that reads a SIDE INPUT beyond `st.snapshot`
    (anything `TrackedSnapshot` cannot observe -- `st.lock`, `st.coverage`,
    `st.tests`, `st.test_policy`, `st.rules`, `st.diff`, `st.queue`) folds
    that input into its returned `extra` tuple via
    `_gate_cache.model_side_channel_key`, so a change to the side input
    ALONE (e.g. `frob ack` rewriting `frob.lock` without touching any
    tracked source file's digest) forces a cache miss instead of serving a
    result computed against the old side state. `parse_failures` and
    `lang_conformance` have no side input beyond the snapshot (and no
    snapshot at all, for `lang_conformance`) and correctly key on `()`."""
    current_date = date.today().isoformat()
    factories = _cacheable_gate_factories(st, current_date)
    if name not in factories:
        raise AssertionError(f"_cacheable_gate_call: {name!r} not in _CACHEABLE_GATES")
    return factories[name]


def _wrap_cacheable(
    root: Path, name: str, st: _GateInputs
) -> Callable[[], tuple[Violation, ...]]:
    """A zero-arg thread-pool job for `name` that goes through
    `_gate_cache.evaluate_cacheable_gate` instead of running unconditionally
    -- same return type/shape as every other `thread_jobs` entry, so
    `_run_combined_jobs` needs no special case for a cached gate."""
    call, extra = _cacheable_gate_call(name, st)
    return lambda: evaluate_cacheable_gate(root, name, st.snapshot, call, extra)


def _build_jobs(
    selected: frozenset[str], st: _GateInputs, *, use_cache: bool = False
) -> tuple[
    dict[str, Callable[[], tuple[Violation, ...]]],
    dict[str, _ProcessJob],
    list[str],
]:
    """Map each selected gate name to a job over the loaded state: a zero-arg
    thread-pool closure for I/O-bound/cheap gates, or a `_ProcessJob`
    (T-0415) for the CPU-bound giants in `_PROCESS_POOL_GATES`.

    T-0602: when `use_cache=True`, every selected gate in `_CACHEABLE_GATES`
    is dispatched through `_gate_cache.evaluate_cacheable_gate` instead of
    its normal unconditional closure -- a cache HIT skips real work, a MISS
    (or no cache entry yet) runs exactly the same call a normal `frob check`
    would. `use_cache=False` (the default, and every existing `frob check`/
    `run_gates` call site) is byte-for-byte the pre-T-0602 behavior -- this
    flag opts a caller IN, it never changes behavior for a caller that does
    not pass it."""
    thread_jobs = _build_thread_jobs(st)
    process_jobs = _build_process_jobs(st)
    selected_thread = {
        name: job for name, job in thread_jobs.items() if name in selected
    }
    selected_process = {
        name: job for name, job in process_jobs.items() if name in selected
    }
    # T-0265: `drift` (DRIFT001/DRIFT002) always runs, even when a caller
    # narrows `selected` to a small subset (e.g. a ticket-scoped
    # `gates={"scope"}` pre-flight check) -- `st.snapshot`/`st.lock` are
    # already unconditionally loaded by `_load_required_state` for every
    # gate run regardless of `selected`, so this costs nothing extra to
    # evaluate. Before this, a narrowly-scoped check could report clean
    # while a full `frob check` on the identical tree reported DRIFT002 for
    # the same dangling edge (a self-referential `frob:tests` directive was
    # the reproducing case) -- two evaluation paths giving two different
    # answers to the same question. DRIFT002 is the documented, authoritative
    # answer for "does this edge endpoint resolve" (docs/modules/gates.md,
    # `test_gate`'s own docstring: "DRIFT002 already covers TESTS edges"),
    # so every gate run now gets that same answer, never a filtered-out one.
    if "drift" not in selected_thread:
        selected_thread["drift"] = thread_jobs["drift"]
    ticket_jobs, skipped = _build_ticket_scoped_jobs(selected, st)
    selected_thread.update(ticket_jobs)
    if use_cache:
        _substitute_cacheable_jobs(selected_thread, st)
    return selected_thread, selected_process, skipped


# frob:ticket T-1049
# frob:ticket T-1340
def _build_thread_jobs(
    st: _GateInputs,
) -> dict[str, Callable[[], tuple[Violation, ...]]]:
    """The thread-pool half of `_build_jobs`'s gate-job registry (I/O-bound/
    cheap gates), split out to keep `_build_jobs` itself under ARCH001's
    line threshold (T-1049 -- the dict-literal assembly, not the
    selection/force-drift/cache-substitution logic around it, was the
    bulk of the function's length)."""
    from frob.policy import policy_gate

    return {
        "drift": lambda: drift_gate(st.snapshot, st.lock),
        "coverage": lambda: coverage_gate(
            st.repo_root,
            st.snapshot,
            st.queue,
            st.diff,
            st.tests,
            st.ticket.id if st.ticket is not None else None,
            st.diff_load_failed,
            st.diff_load_no_repo,
            st.python_collection_failed,
        ),
        "invariant": lambda: (
            *invariant_gate(st.invariants, st.snapshot, st.tests, st.rule_ids),
            *inv003_gate(st.repo_root, st.invariants),
            *inv004_gate(st.repo_root),
            *inv006_gate(st.repo_root, st.snapshot),
            # T-0757: import-forbidding (INV007) and establish-property
            # (INV008) obligations declared via `frob:invariant`'s
            # `no_import=`/`establishes=` attrs -- see
            # `frob.gates._design_invariants`.
            *inv007_violations(st.repo_root, st.snapshot),
            *inv008_violations(st.snapshot),
        ),
        "test": lambda: test_gate(
            st.snapshot, st.systems, st.coverage, st.tests, st.test_policy
        ),
        "policy": lambda: policy_gate(st.rules, st.snapshot, st.diff),
        "doclink": lambda: doclink_gate(st.root, st.snapshot),
        # T-0314: docanchor resolves frob:doc <file>#<anchor> targets, which
        # are repo-relative path text -- always against repo_root, never the
        # (possibly scoped) st.root, so `frob check <subdir>` reports the
        # same DOC002 result as the unscoped run.
        "docanchor": lambda: docanchor_gate(st.repo_root, st.snapshot),
        # T-1232: docs/audits/*.md status headers, repo_root-scoped like
        # docanchor above (a scoped `frob check <subdir>` must still see
        # the whole docs/audits/ tree).
        "docstatus": lambda: docstatus_gate(st.repo_root),
        # T-1230: Makefile target citations, repo_root-scoped like
        # docstatus/docanchor above.
        "docmake": lambda: docmake_gate(st.repo_root, st.snapshot),
        # T-0436: fenced-code-block doc-drift heuristic, repo_root-scoped for
        # the same reason docanchor/refs are -- doc paths are repo-relative
        # text either way, and `git ls-files *.md` must see the whole repo.
        # T-0435: DOC005 (README command-table drift-lock) fires alongside
        # DOC004 under the same "docblocks" gate name -- one config
        # ([[docblocks.commands]]), one live-registry walk, two checks.
        # T-0437: DOC006 (doc-pointer resolution over a closed set of
        # recognized shapes) rides alongside DOC004/DOC005 under the same
        # "docblocks" gate name -- same repo-wide doc-drift concern, same
        # `_docblocks` config surface it reuses (`_console_command_sources`/
        # `_console_trees`), no new stage-group registration needed.
        # T-1227: DOCENUM001 (frob:enumerates member-list AST-diff) rides
        # alongside DOC004/DOC005/DOC006 under the same "docblocks" gate
        # name -- same repo-wide doc-drift concern, no new stage-group
        # registration needed (DOC006's own precedent).
        # T-1229: NEGEXIST001 (frob:until-bound negative-existence claims)
        # rides alongside DOC004/DOC005/DOC006/DOCENUM001 under the same
        # "docblocks" gate name -- same repo-wide doc-drift concern, no
        # new stage-group registration needed (DOCENUM001's own precedent).
        "docblocks": lambda: (
            *doc004_gate(st.repo_root, st.snapshot),
            *doc005_gate(st.repo_root),
            *doc006_gate(st.repo_root, st.snapshot),
            *docenum001_gate(st.repo_root, st.snapshot),
            *negexist001_gate(st.snapshot, st.queue),
        ),
        "fuzz": lambda: fuzz_gate(st.root, st.snapshot),
        # T-1340: SUPPRESS001, evidence-driven suppression-dialect
        # mismatch detection -- I/O-bound (spawns ty/mypy oracle
        # subprocesses), same thread-pool shape as "fuzz" above, not a
        # CPU-bound _PROCESS_POOL_GATES candidate.
        "suppress": lambda: suppress001_gate(st.root, st.snapshot),
        "release": lambda: release_gate(
            st.root, st.snapshot, st.ticket.id if st.ticket is not None else None
        ),
        "decisions": lambda: decisions_gate(st.root, st.snapshot),
        "tickets": lambda: tickets_gate(st.root, st.queue),
        # T-0788: COMPLIANCE005, always against repo_root (never the
        # possibly-scoped st.root) -- docs/design/registry/compliance.yaml
        # is a repo-wide manifest, same reasoning as "registry" below.
        "compliance": lambda: compliance_gate(st.repo_root),
        # T-0412: current_date/current_version are injected (debt_gate stays
        # a pure function of its args, matching every other gate here) --
        # an unresolvable version degrades to "0.0.0" so a repo with no
        # pyproject.toml still gets the date-based expiry check.
        "debt": lambda: debt_gate(
            st.snapshot,
            st.queue,
            current_date=date.today().isoformat(),
            current_version=_current_version(st.repo_root) or "0.0.0",
        ),
        # T-0576: same injected-current_date posture as "debt" above --
        # deprecated_gate stays a pure function of its args. T-0639:
        # DEPR005 additionally needs repo_root to resolve
        # frob-deprecated-baseline.lock.json and the live reference set.
        "deprecated": lambda: deprecated_gate(
            st.snapshot,
            st.queue,
            st.repo_root,
            current_date=date.today().isoformat(),
        ),
        # T-0465: `.git/info/exclude` is the SHARED common-dir file across
        # every worktree of this clone, always against repo_root (never
        # the possibly-scoped st.root) for the same reason secrets/refs
        # are -- the hazard is repo-wide by construction.
        "excludehazard": lambda: exclude_hazard_gate(st.repo_root),
        # T-0396: whole-repo scan, always against repo_root (never the
        # possibly-scoped st.root) -- a `frob check <subdir>` run must see
        # the same inbound-reference graph as an unscoped run, same
        # reasoning as docanchor above.
        "refs": lambda: ref_gate(st.repo_root),
        # T-0558: PARSE001, one violation per snapshot.parse_failures entry.
        "parse_failures": lambda: parse_failure_gate(st.snapshot),
        # T-0343: fail-closed exhaustiveness drift-lock over
        # docs/design/registry/*.yaml -- known_rules is this run's live
        # gate-rule-id + policy-rule-id union, never a hardcoded list, so
        # handled_by:<rule-id> is verified against what this build
        # actually enforces.
        "registry": lambda: registry_gate(
            st.repo_root,
            st.queue,
            _KNOWN_GATE_RULES | st.rule_ids,
            snapshot=st.snapshot,
        ),
        # T-0405: takes no repo-scanned state -- reads the live in-process
        # `frob.lang` language-support registry directly.
        "lang_conformance": lambda: lang_conformance_gate(),
        # T-0406: always against repo_root (never the possibly-scoped
        # st.root) -- a repo's real language mix is a repo-wide concern,
        # same reasoning as refs/secrets/walk_lint above. T-0823: no
        # longer takes st.queue -- LANG003 verifies known-gap tickets
        # against frob's own shipped registry, not the checked repo's
        # queue.
        "lang_project_conformance": lambda: project_lang_conformance_gate(st.repo_root),
        # T-0851: FMT001, diff-scoped like TODO001/coverage above -- always
        # against repo_root so a `frob check <subdir>` run resolves the same
        # repo-relative diff hunk paths coverage_gate's TODO001 half does.
        "fmt": lambda: fmt_gate(st.repo_root, st.diff),
        # T-0628: AFFECT001/AFFECT002, diff-scoped like coverage/fmt above --
        # touched_symrefs/touched_files are already computed against
        # st.diff/st.snapshot by _build_jobs' shared helpers.
        "affect_drift": lambda: affect_drift_gate(st.snapshot, st.diff),
    }


# frob:ticket T-1049
def _build_process_jobs(st: _GateInputs) -> dict[str, _ProcessJob]:
    """The process-pool half of `_build_jobs`'s gate-job registry (the
    CPU-bound giants in `_PROCESS_POOL_GATES`), split out alongside
    `_build_thread_jobs` for the same ARCH001 reason."""
    return {
        "perf": _ProcessJob(perf_gate, (st.root, st.snapshot)),
        "clones": _ProcessJob(dup_gate, (st.root, st.snapshot, st.diff)),
        "sys": _ProcessJob(sys_gate, (st.root, st.snapshot)),
        "secrets": _ProcessJob(secrets_gate, (st.root,)),
        # T-0781: SEC005, WARN-tier at first turn-on (same opaque_gate/
        # T-0688 promotion posture) -- repo-writable .git/.frob state
        # reaching a subprocess argv sink with no validator hop or `--`.
        "taint": _ProcessJob(taint_gate, (st.root,)),
        # T-0665: OPAQUE001, WARN-tier at first turn-on (see opaque_gate's
        # own docstring for the T-0688/T-0973 promotion precedent this
        # follows) -- same repo-wide tracked-file scan shape as secrets.
        "opaque": _ProcessJob(opaque_gate, (st.root,)),
        "archgate": _ProcessJob(arch_gate, (st.root,)),
        # T-0688: EXHAUST001/EXHAUST002, always against repo_root (never
        # the possibly-scoped st.root) -- same reasoning as `archgate`/
        # `pii_structural`: a `frob check <subdir>` run should see the same
        # per-function exhaustiveness verdicts an unscoped run would, since
        # a leaked exception from a same-module callee outside the scoped
        # subdir is still a real, repo-wide correctness concern.
        "exhaustive_handling": _ProcessJob(exhaustive_handling_gate, (st.root,)),
        # T-0690: FFI001/FFI002 -- FFI001 always cross-checks pyo3
        # boundaries repo-wide internally (see `ffi_boundary_gate`'s own
        # docstring), FFI002 scans the possibly-scoped `st.root`, same
        # split reasoning as `exhaustive_handling` above.
        "ffi_boundary": _ProcessJob(ffi_boundary_gate, (st.root, st.repo_root)),
        "pii_structural": _ProcessJob(pii_structural_gate, (st.root,)),
        # T-0471: whole-repo tracked-file scan, always against repo_root
        # (never the possibly-scoped st.root) -- same reasoning as
        # `pii_structural`/`refs`: `frob check <subdir>` must see the same
        # WALK001 result as an unscoped run since a raw traversal call
        # anywhere in src/frob/ is a repo-wide concern, not a subdir one.
        "walk_lint": _ProcessJob(walk_lint_gate, (st.repo_root,)),
        # T-0439: whole-repo tracked-file scan, always against repo_root --
        # same reasoning as secrets/walk_lint above: a CVE-fingerprint
        # needle anywhere in the tree is a repo-wide concern, not a
        # subdir-scoped one.
        "cve_fingerprint_scan": _ProcessJob(cve_fingerprint_scan_gate, (st.repo_root,)),
        # T-0459: whole-repo tracked-file scan, always against repo_root --
        # same reasoning as walk_lint above: a bare stdout write anywhere in
        # src/frob/ is a repo-wide concern, not a subdir-scoped one.
        "render_lint": _ProcessJob(render_lint_gate, (st.repo_root,)),
        # T-0422: per-package build_call_graph calls are CPU-bound like the
        # rest of this pool (archgate/perf/sys), not I/O-bound.
        "dead_symbols": _ProcessJob(dead_symbol_gate, (st.root, st.snapshot)),
        # T-1428: same CPU-bound-pool posture as dead_symbols above -- a
        # repo-wide text scan (see wire_gate's own docstring for why it is
        # a scan, not a call-graph query) plus a small waive-edge pass.
        "wire": _ProcessJob(wire_gate, (st.root, st.snapshot, st.diff, st.queue)),
        # T-0813: same CPU-bound per-package build_call_graph posture as
        # dead_symbols above, plus a fixpoint pass over each package's
        # protocol-tagged symbols.
        "protocol_summary": _ProcessJob(protocol_summary_gate, (st.root, st.snapshot)),
    }


# frob:ticket T-0602
def _substitute_cacheable_jobs(
    selected_thread: dict[str, Callable[[], tuple[Violation, ...]]], st: _GateInputs
) -> None:
    """`_build_jobs`'s `use_cache=True` step, split out to keep `_build_jobs`
    itself under ARCH001's line threshold: replace every selected gate in
    `_CACHEABLE_GATES` with a cache-aware job (`_wrap_cacheable`) in place --
    "drift" (which `_build_jobs` may have force-added even when unselected)
    is included too, so an unconditionally-forced drift check gets the same
    cache benefit a directly-selected one would. Mutates `selected_thread`
    in place; returns nothing."""
    for name in list(selected_thread):
        if name in _CACHEABLE_GATES:
            selected_thread[name] = _wrap_cacheable(st.repo_root, name, st)


def _b9_exempt_file(file: str) -> bool:
    """Files a no-active-ticket diff may touch without tripping B9: the
    `tickets.md` ledger (archiving closed tickets is a legitimate no-ticket,
    direct-to-main operation) and frob's own local `.frob/` state (never
    real source, regardless of gitignore status)."""
    return file == "tickets.md" or file.startswith(".frob/")


def _no_active_ticket_touches_source(diff: Diff) -> bool:
    """True if `diff` touches any file besides the B9-exempt set (ticket
    ledger, `.frob/` local state): any other touched file with no derivable
    active ticket is exactly the SCOPE001/PRE001 escape B9 closes."""
    return any(not _b9_exempt_file(f) for f in _touched_files(diff))


# frob:ticket T-0541
def _no_active_ticket_violation(rule: str, diff: Diff) -> tuple[Violation, ...]:
    """SCOPE001/PRE001 (B9): the diff touches source but no active ticket is
    derivable (no `--ticket` and no `T-####-` branch prefix). Previously
    this silently skipped both scope and pre-work enforcement entirely; now
    it is a loud blocking violation instead, since skipping is exactly the
    escape an off-convention branch (or committing on `main`) could exploit."""
    touched = sorted(f for f in _touched_files(diff) if not _b9_exempt_file(f))
    return (
        Violation(
            rule=rule,
            severity=Severity.ERROR,
            file=touched[0] if touched else "",
            line=0,
            message=(
                f"{rule}: diff touches {len(touched)} file(s) but no active "
                "ticket is derivable (pass --ticket or use a T-####-name "
                "branch); scope/pre-work enforcement cannot be skipped"
            ),
        ),
    )


# frob:ticket T-0541
def _build_ticket_scoped_jobs(
    selected: frozenset[str], st: _GateInputs
) -> tuple[dict[str, Callable[[], tuple[Violation, ...]]], list[str]]:
    """`scope`/`prework` jobs both need `st.ticket`. When no ticket is
    derivable AND the diff touches non-ledger source (B9), that is now a
    loud blocking violation instead of a silent skip; jobs are only truly
    skipped (not run, not failed) when there is nothing to enforce against.

    PRE001 also blocks loudly (rather than silently skipping) when the
    working diff itself failed to load and no ticket is derivable: a
    failed diff degrades to an empty placeholder that looks like "nothing
    touched" to `no_ticket_blocks`, which is exactly the B9 escape reached
    through a different door (detached HEAD / bad `--base` instead of an
    off-convention branch name). SCOPE001 already had this via its own
    unconditional `diff_load_failed` check; PRE001 did not.

    T-0719: SCOPE001's `diff_load_failed` check narrows to `diff_load_failed
    and not diff_load_no_repo` -- a genuinely git-less `root` (no `.git`
    anywhere above it, e.g. a fixture that never calls `git init`) has
    structurally no touched set to enforce SCOPE001 against, so it is
    treated the same as a clean/empty diff instead of the loud
    `_diff_load_failed_violation`. PRE001's own `diff_load_failed` branch
    below is deliberately left unconditional (not narrowed the same way):
    a no-ticket, no-repo root is still the B9 shape PRE001 exists to
    catch, and narrowing it would silently reopen that escape."""
    jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {}
    skipped: list[str] = []
    no_ticket_blocks = st.ticket is None and _no_active_ticket_touches_source(st.diff)
    if "scope" in selected:
        scope_ticket = st.ticket
        if st.diff_load_failed and not st.diff_load_no_repo:
            # T-0550/B8: a failed diff load must not silently clear SCOPE001
            # just because its degraded-empty placeholder touches nothing.
            jobs["scope"] = lambda: (
                _diff_load_failed_violation("SCOPE001", st.diff.base),
            )
        elif scope_ticket is not None:
            jobs["scope"] = lambda: scope_gate(
                st.diff, scope_ticket, st.snapshot, root=st.root, queue=st.queue
            )
        elif no_ticket_blocks:
            jobs["scope"] = lambda: _no_active_ticket_violation("SCOPE001", st.diff)
        else:
            skipped.append("scope")
    if "prework" in selected:
        pre_ticket = st.ticket
        if pre_ticket is not None:
            jobs["prework"] = lambda: prework_gate(pre_ticket, st.snapshot, st.sweep)
        elif st.diff_load_failed:
            # T-0541 (B9 remainder): a failed diff load degrades `st.diff`
            # to `_load_diff`'s empty placeholder, so `no_ticket_blocks`
            # (which asks the diff what it touched) would see zero touched
            # files and skip PRE001 -- the exact detached-HEAD/bad-`--base`
            # shape B9 exists to close, just reached through the diff-load
            # path instead of the branch-naming path. Mirror SCOPE001's
            # already-loud `diff_load_failed` handling here instead of
            # silently trusting the degraded-empty diff.
            jobs["prework"] = lambda: (
                _diff_load_failed_violation("PRE001", st.diff.base),
            )
        elif no_ticket_blocks:
            jobs["prework"] = lambda: _no_active_ticket_violation("PRE001", st.diff)
        else:
            skipped.append("prework")
    return jobs, skipped


# frob:ticket T-0232
# frob:tests tests/test_gates.py::TestRunJobsTimingAttribution.test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing  # noqa: E501
def _timed_job(
    job: Callable[[], tuple[Violation, ...]],
) -> Callable[[], tuple[tuple[Violation, ...], float]]:
    """Wrap `job` to self-report its own CPU time (T-0232): `time.thread_time()`
    measured from inside the worker thread the job actually runs on, start to
    finish, so the number reflects only that thread's own CPU consumption.

    `_run_jobs` used to time each job from the *submitting* thread with
    `time.monotonic()` around `future.result()` -- wall-clock elapsed. Most
    gate jobs here are pure-Python, CPU-bound work (file scanning, regex,
    AST walks) sharing one `ThreadPoolExecutor`, so they all contend for the
    same GIL: with N such jobs running "concurrently", each gets roughly
    1/N of the CPU, so wall-clock elapsed converges toward the *sum* of
    every job's own cost, not that job's own cost -- every gate's reported
    time ends up nearly identical to the slowest one's, regardless of how
    little work it actually did (measured directly: on this repo, `sys`
    reported 14.63s wall vs. 2.00s of its own CPU time; `tickets` 1.53s wall
    vs. 0.53s CPU -- the wall numbers cluster together, the CPU numbers
    don't). `thread_time()` is immune to this: it counts only the calling
    thread's own scheduled CPU time, so a job that is genuinely blocked
    waiting for the GIL (not running) does not accrue it.
    """

    def run() -> tuple[tuple[Violation, ...], float]:
        cpu_start = time.thread_time()
        result = job()
        return result, time.thread_time() - cpu_start

    return run


# frob:tests tests/test_gates.py::TestRunJobsTimingAttribution.test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing  # noqa: E501
def _run_jobs(
    jobs: dict[str, Callable[[], tuple[Violation, ...]]],
) -> tuple[list[Violation], dict[str, int], dict[str, float]]:
    """Run the gate jobs in parallel; return merged violations, counts,
    and each job's own CPU time (T-0232, `_timed_job`) rather than wall
    time distorted by GIL contention among the other jobs running at once."""
    counts: dict[str, int] = {}
    timing: dict[str, float] = {}
    violations: list[Violation] = []
    if not jobs:
        return violations, counts, timing
    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {name: pool.submit(_timed_job(job)) for name, job in jobs.items()}
        for name, future in futures.items():
            result, cpu_elapsed = future.result()
            timing[name] = cpu_elapsed
            counts[name] = len(result)
            violations.extend(result)
            _log.info(
                "run_gates: %s -> %d violation(s) in %.3fs cpu",
                name,
                len(result),
                cpu_elapsed,
            )
    return violations, counts, timing


#: T-0806: env var `_open_process_pool` stamps with the parent's CURRENT
#: stdout log handler level (`logging.getLevelName`) before spawning any
#: worker. `ProcessPoolExecutor(mp_context=spawn)` workers are fresh
#: interpreters that re-run `frob.logging.logger._init()` from scratch on
#: first import -- they never see the parent's in-memory
#: `quiet_stdout_logs`/`stdout_log_level` clamp (that mutates the PARENT
#: process's handler objects only), so a `--json`/quiet parent run used to
#: leak every worker's own default-DEBUG per-file parse logging straight
#: onto the stdout file descriptor the worker inherits from the parent
#: (observed corrupting `frob check --json`'s stdout payload and the
#: default/`-v`-gated `frob check` text output alike -- tests/system/
#: test_cli_check.py's `TestCheckCleanProject`/`TestCheckPolyglot`/
#: `TestCheckVerbosity` fixtures, none of which are git repos, both
#: reliably exercise `arch_gate`'s process-pool path and have no `.git`
#: noise to mask it). Env vars set before pool construction are inherited
#: by every spawned worker, so this is visible to `_run_process_gate`
#: (below) the moment its own module import chain re-runs `_init()`.
# frob:ticket T-0806
_WORKER_STDOUT_LOG_LEVEL_ENV = "FROB_WORKER_STDOUT_LOG_LEVEL"


# frob:ticket T-0415
# frob:ticket T-0806
def _run_process_gate(
    func: Callable[..., tuple[Violation, ...]], args: tuple
) -> tuple[tuple[Violation, ...], float]:
    """Picklable `ProcessPoolExecutor` entry point (T-0415): run one
    CPU-bound gate (`func(*args)`) in its own worker process and return its
    own `time.process_time()` -- accurate here (unlike a shared thread pool,
    T-0232) because each worker process runs exactly one job, so there is no
    sibling job to contend with for CPU. Must stay a module-level function
    (not a closure/lambda) so `pickle` can address it by `__module__` +
    `__qualname__` when the parent ships the call to a worker.

    T-0806: before running `func`, clamps this worker's OWN stdout log
    handler(s) to `_WORKER_STDOUT_LOG_LEVEL_ENV`'s value when set -- see
    that constant's docstring for why a worker process needs this at all
    (it never inherits the parent's in-memory logging clamp, only its
    environment)."""
    # frob:waive SEC110 reason="worker log-level marker, not a secret"
    level_name = os.environ.get(_WORKER_STDOUT_LOG_LEVEL_ENV)
    if level_name:
        from frob.logging.quiet import _stdout_stream_handlers

        # T-1185: `logging.getLevelNamesMapping()` (dict lookup) replaces
        # `getattr(logging, level_name)` (OPAQUE001 getattr-dynamic-name) --
        # `level_name` is always one of `logging.getLevelNamesMapping()`'s own
        # keys, written by `_stamp_worker_stdout_log_level_env` via
        # `logging.getLevelName(...)`'s reverse, so the lookup can never miss.
        for handler in _stdout_stream_handlers():
            handler.setLevel(logging.getLevelNamesMapping()[level_name])
    cpu_start = time.process_time()
    result = func(*args)
    return result, time.process_time() - cpu_start


# frob:ticket T-0415
def _drain_futures(
    futures: dict[str, Future[tuple[tuple[Violation, ...], float]]],
    raw: dict[str, tuple[Violation, ...]],
    counts: dict[str, int],
    timing: dict[str, float],
    *,
    pool_label: str,
) -> None:
    """Collect `futures` (from either pool) into the shared `raw`/`counts`/
    `timing` accumulators `_run_combined_jobs` merges afterward (T-0415)."""
    for name, future in futures.items():
        result, cpu_elapsed = future.result()
        raw[name] = result
        timing[name] = cpu_elapsed
        counts[name] = len(result)
        _log.info(
            "run_gates: %s -> %d violation(s) in %.3fs cpu%s",
            name,
            len(result),
            cpu_elapsed,
            pool_label,
        )


# frob:ticket T-0581
def _submit_process_pool(
    ppool: ProcessPoolExecutor, process_jobs: dict[str, _ProcessJob]
) -> dict[str, Future[tuple[tuple[Violation, ...], float]]]:
    """Submit every `process_jobs` entry to `ppool` and return the futures
    without draining them (T-0581) -- submission must happen (and the pool's
    worker processes must be forked/spawned) before `_run_combined_jobs`
    opens its `ThreadPoolExecutor`, so callers drain these futures
    separately, after the thread pool's own work is queued."""
    return {
        name: ppool.submit(_run_process_gate, job.func, job.args)
        for name, job in process_jobs.items()
    }


# frob:doc docs/modules/gates.md#error-types
class GateOrderDriftError(RuntimeError):
    """T-0839: raised by `_merge_canonical_order` when `raw` names a gate
    absent from `_CANONICAL_GATE_ORDER` -- unrecoverable wiring drift
    between `_ALL_GATES`/`_build_jobs` and the order tuple, never a
    legitimate runtime condition a caller should catch and continue past."""

    def __init__(self, missing_gates: list[str]) -> None:
        """Store `missing_gates` and build the loud, actionable message."""
        self.missing_gates = missing_gates
        super().__init__(
            "gate(s) "
            f"{missing_gates} produced results but are missing from "
            "_CANONICAL_GATE_ORDER -- add them to the order tuple "
            "(src/frob/gates/__init__.py) so their violations are not "
            "silently dropped from frob check output"
        )


def _merge_canonical_order(raw: dict[str, tuple[Violation, ...]]) -> list[Violation]:
    """Flatten `raw` (gate name -> its violations) into one list ordered by
    `_CANONICAL_GATE_ORDER` (T-0415) -- the fixed order the old single-pool
    `_build_jobs` dict used, so output stays identical regardless of which
    pool produced a given gate's result first.

    T-0839: `raw` naming a gate absent from `_CANONICAL_GATE_ORDER` is a
    wiring-drift programmer bug (a gate registered in `_ALL_GATES`/
    `_build_jobs` but never added to the order tuple), never a legitimate
    runtime state -- silently dropping that gate's findings is exactly the
    live incident this ticket exists to close (T-0788's "compliance" gate
    briefly had this gap). Raise loudly instead of degrading quietly."""
    unknown = sorted(set(raw) - set(_CANONICAL_GATE_ORDER))
    if unknown:
        _log.error(
            "_merge_canonical_order: gate(s) %s present in raw results but "
            "missing from _CANONICAL_GATE_ORDER -- their violations would "
            "be silently dropped",
            unknown,
        )
        raise GateOrderDriftError(unknown)
    violations: list[Violation] = []
    for name in _CANONICAL_GATE_ORDER:
        if name in raw:
            violations.extend(raw[name])
    return violations


#: T-0947: preloaded once inside the `forkserver` helper process's own
#: startup (not per-worker) when that context is used -- `frob.gates`
#: transitively imports every process-pool gate's home module (`frob.perf`,
#: `frob.dup`, `frob.arch`, ...) as well as `frob_core`/`strata_core`, so
#: importing this one name absorbs the whole cold-import cost this
#: ticket measured. Kept as a private module-level constant (not inlined)
#: so `_open_process_pool` and any future direct test of the preload list
#: read the same value.
# frob:ticket T-0947
_FORKSERVER_PRELOAD: tuple[str, ...] = ("frob.gates",)


def _process_pool_start_method() -> str:
    """Pick `forkserver` when this platform's `multiprocessing` offers it
    (T-0947), else fall back to `spawn`. Both start methods share the
    T-0581 safety property this module depends on -- the new worker
    process is launched via a fresh `exec`, never a raw `fork()` of the
    (possibly multi-threaded) calling process -- `forkserver` only forks
    from its own single-threaded helper process, which is why the
    upstream `multiprocessing` docs call that helper safe to `fork()`
    from regardless of how many threads the ORIGINAL caller has. `fork`
    (bare, no exec) is never selected here; see `_run_combined_jobs`'s
    docstring for why that one is unsafe on this code path."""
    if "forkserver" in multiprocessing.get_all_start_methods():
        return "forkserver"
    return "spawn"


# frob:ticket T-0806
# frob:ticket T-0990
# frob:tests tests/test_gates.py::TestProcessPoolGates.test_open_process_pool_preloads_forkserver_when_available  # noqa: E501
def _stamp_worker_stdout_log_level_env() -> None:
    """Stamp `_WORKER_STDOUT_LOG_LEVEL_ENV` with the parent's current
    stdout log handler level, BEFORE `_open_process_pool` constructs its
    pool (workers start as soon as the pool exists, not on first
    `submit`), so every worker `_run_process_gate` runs in clamps its own
    default-DEBUG logging to match -- see `_WORKER_STDOUT_LOG_LEVEL_ENV`'s
    docstring. Split out of `_open_process_pool` (T-0990) so each env-
    marker stamp stays a single, low-branch-count concern of its own --
    the ARCH103 mixed-concern-function check flags a function only once
    it mixes I/O, string-formatting, AND 2+ of its own decision points,
    and no one of these stamp helpers alone reaches that bar."""
    from frob.logging.quiet import _stdout_stream_handlers

    handlers = _stdout_stream_handlers()
    if handlers:
        # frob:waive SEC110 reason="worker log-level marker, not a secret"
        os.environ[_WORKER_STDOUT_LOG_LEVEL_ENV] = logging.getLevelName(
            handlers[0].level
        )


# frob:ticket T-0982
# frob:ticket T-0990
# frob:tests tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_real_pool_worker_under_parent_shared_holder_completes  # noqa: E501
def _stamp_worker_lock_keys_env() -> None:
    """Stamp `frob.process._lock._INHERITED_LOCK_KEYS_ENV` with this (the
    pool OWNER's) own `held_registry_keys()` snapshot, BEFORE
    `_open_process_pool` constructs its pool, for the same env-inheritance
    reason `_stamp_worker_stdout_log_level_env` stamps its own marker. This
    is what lets a gate that runs `derived_state_write_lock` inside a pool
    worker (e.g. `dup_gate` via `find_clones`) see that the process which
    spawned it already holds `derived_state_lock` for that root -- without
    this, a worker forked/spawned while `run_gates`'s own caller (`frob
    check`'s main process, see `frob.check`) holds the run-wide SHARED lock
    would issue a real, blocking `flock(LOCK_EX)` against that SHARED hold
    and deadlock forever (T-0982, lslocks-confirmed; the cross-process
    sibling of T-0918's same-process case). See
    `frob.process._lock._worker_inherits_hold`'s docstring for the reader
    side of this marker. Split out of `_open_process_pool` (T-0990) -- see
    `_stamp_worker_stdout_log_level_env`'s docstring for why."""
    from frob.process._lock import _INHERITED_LOCK_KEYS_ENV as _LOCK_KEYS_ENV
    from frob.process._lock import _INHERITED_LOCK_KEYS_SEP as _LOCK_KEYS_SEP
    from frob.process._lock import held_registry_keys

    held_keys = held_registry_keys()
    if held_keys:
        # frob:waive SEC110 reason="lock-registry-key marker (a resolved filesystem \
        # path), not a secret"
        os.environ[_LOCK_KEYS_ENV] = _LOCK_KEYS_SEP.join(held_keys)


# frob:ticket T-1464
def _stamp_worker_parse_artifact_cache_env(root: Path) -> None:
    """Stamp `frob.lang.PARSE_ARTIFACT_CACHE_ENV` with `root`'s resolved
    `.frob/parse-artifacts.db` path (`_parse_artifact_cache_path`), BEFORE
    `_open_process_pool` constructs its pool
    (same env-inheritance timing `_stamp_worker_stdout_log_level_env`/
    `_stamp_worker_lock_keys_env` depend on, T-0806/T-0982): every worker
    `_run_process_gate` spawns then sees the SAME path and can open a
    shared connection to it (`frob.lang._artifact_cache_connection`), so
    per-file parse artifacts derived by one worker (perf/clones/
    dead_symbols/arch/sys/pii, T-1217's root-cause finding) become visible
    to every sibling worker instead of each independently re-parsing +
    re-extracting the whole repo (T-1464).

    Also creates/migrates the db file HERE, once, in the parent, via
    `frob.graph.cache.connect()` -- NOT lazily inside each worker's first
    `_artifact_cache_connection()` call. `N` workers all racing
    `_apply_schema_with_recovery`'s own lock-poll-retry dance on a brand
    new, same-named db file at once (every worker's first parse call
    landing in the same few-hundred-ms window right after pool startup)
    measurably perturbed this PROCESS's overall timing enough to newly
    expose an unrelated, pre-existing latent race in `build_graph`'s own
    concurrent-first-open path against `.frob/cache.db` (a T-1464 incident:
    `store_file_data(...)  still locked after 30s`, on a code path this
    ticket's scope does not touch and does not itself explain) -- doing
    the one-time ensure-schema work exactly once, before any worker
    exists, removes that self-inflicted contention burst entirely; workers
    then only ever open an ALREADY-VALID db file, no schema/fingerprint
    work of their own."""
    from frob.lang import PARSE_ARTIFACT_CACHE_ENV

    cache_path = _parse_artifact_cache_path(root)
    from frob.graph import cache as _graph_cache

    try:
        _graph_cache.connect(cache_path).close()
    except Exception:
        _log.warning(
            "parse-artifact cache at %s could not be prepared, workers will "
            "fall back to uncached parsing",
            cache_path,
            exc_info=True,
        )
        return
    # frob:waive SEC110 reason="cache-db filesystem path marker, not a secret"
    os.environ[PARSE_ARTIFACT_CACHE_ENV] = str(cache_path)


# frob:ticket T-0767
# frob:ticket T-0806
# frob:ticket T-0947
# frob:ticket T-0990
def _open_process_pool(
    process_jobs: dict[str, _ProcessJob],
    *,
    root: Path | None = None,
    max_workers: int | None = None,
) -> ProcessPoolExecutor:
    """Construct the `ProcessPoolExecutor` for `process_jobs` (which must be
    non-empty). Hoisted out of `_run_combined_jobs` (T-0767) so no single
    function constructs BOTH pools -- the T-0695 `pool-inside-pool`
    advisory is a same-function co-occurrence heuristic and unwaivable by
    design, so the safe shape must also be the structurally clean one.

    T-0947: uses `forkserver` (falling back to `spawn` where unavailable,
    `_process_pool_start_method`) with `_FORKSERVER_PRELOAD` imported once
    in the forkserver helper process, instead of `spawn`'s per-worker cold
    import. Measured cause (docs/audits/check-performance.md Finding 3,
    T-0947's own isolation pass): each `spawn` worker cold-imports
    `frob.gates` itself before running its job, at ~0.5-0.7s per worker
    (NOT the ~18s the audit's back-of-envelope estimate guessed) --
    `forkserver` pays that import cost once, in its own helper process,
    then every actual worker forks from an already-imported helper at
    near-zero cost. Measured with the helper pre-warmed: per-worker
    spawn-to-start latency dropped from ~0.53-0.74s (spawn) to
    ~0.24-0.47s (forkserver+preload) on this repo's own `gates-native`
    job set -- see T-0947's Done report for the exact before/after
    numbers. `mp_context` choice does NOT change T-0581's fix: neither
    `spawn` nor `forkserver` ever raw-forks the (possibly multi-threaded)
    calling process directly, which is the property T-0581's fix actually
    depends on -- do not swap either for bare `fork`.

    T-0806: stamps `_WORKER_STDOUT_LOG_LEVEL_ENV` with the parent's current
    stdout log handler level BEFORE constructing the pool (workers start
    as soon as the pool exists, not on first `submit`) so every worker
    `_run_process_gate` runs in clamps its own default-DEBUG logging to
    match -- see `_WORKER_STDOUT_LOG_LEVEL_ENV`'s docstring.

    T-0982: also stamps `frob.process._lock._INHERITED_LOCK_KEYS_ENV` with
    this (the pool OWNER's) own `held_registry_keys()` snapshot, BEFORE
    constructing the pool, for the same env-inheritance reason. This is
    what lets a gate that runs `derived_state_write_lock` inside a pool
    worker (e.g. `dup_gate` via `find_clones`) see that the process which
    spawned it already holds `derived_state_lock` for that root -- without
    this, a worker forked/spawned while `run_gates`'s own caller (`frob
    check`'s main process, see `frob.check`) holds the run-wide SHARED lock
    would issue a real, blocking `flock(LOCK_EX)` against that SHARED hold
    and deadlock forever (T-0982, lslocks-confirmed; the cross-process
    sibling of T-0918's same-process case). See
    `frob.process._lock._worker_inherits_hold`'s docstring for the reader
    side of this marker. T-0990: the two env-marker stamps themselves now
    live in `_stamp_worker_stdout_log_level_env`/`_stamp_worker_lock_keys_env`
    (each a single, low-branch-count concern), called here before pool
    construction exactly as the inline code used to run.

    T-1436: `max_workers`, when given, caps the pool BELOW the normal
    `min(len(process_jobs), cpu_count())` bound instead of replacing it --
    a caller that already knows it is competing for CPU with something
    else on the same box (the warm daemon's own `frob_check_delta`, see
    `frob.serve._tools._DAEMON_GATE_MAX_WORKERS`) passes a smaller number
    here to size its pool down; every other caller passes `None` (the
    default) and gets the unchanged pre-T-1436 behavior.

    T-1464: also stamps `frob.lang.PARSE_ARTIFACT_CACHE_ENV` with `root`'s
    resolved `.frob/parse-artifacts.db` path, same env-inheritance timing
    as the other two stamps -- see `_stamp_worker_parse_artifact_cache_env`.
    `root=None` (a caller that predates T-1464, or a test exercising this
    helper directly) skips the stamp entirely -- workers just see no
    persistent artifact cache configured, the same passthrough behavior
    `frob.lang._artifact_cache_connection` already has for an unset env
    var."""
    _stamp_worker_stdout_log_level_env()
    _stamp_worker_lock_keys_env()
    if root is not None:
        _stamp_worker_parse_artifact_cache_env(root)
    # Bounded worker count (constraint 4): never more workers than
    # jobs, never more than the machine's CPU count.
    proc_workers = max(1, min(len(process_jobs), os.cpu_count() or 4))
    if max_workers is not None:
        proc_workers = max(1, min(proc_workers, max_workers))
    ctx = multiprocessing.get_context(_process_pool_start_method())
    if ctx.get_start_method() == "forkserver":
        ctx.set_forkserver_preload(list(_FORKSERVER_PRELOAD))
    return ProcessPoolExecutor(
        max_workers=proc_workers,
        mp_context=ctx,
    )


# frob:ticket T-0767
def _run_thread_jobs(
    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]],
    raw: dict[str, tuple[Violation, ...]],
    counts: dict[str, int],
    timing: dict[str, float],
) -> None:
    """Open the `ThreadPoolExecutor`, submit every `thread_jobs` entry, and
    drain the futures into the shared accumulators. Hoisted out of
    `_run_combined_jobs` (T-0767) so the thread-pool construction lives in
    a different function from the process-pool construction
    (`_open_process_pool`) -- see that helper's docstring for why. By the
    time this runs, `_run_combined_jobs` has already created the process
    pool and submitted its jobs (T-0581 ordering)."""
    with ThreadPoolExecutor(max_workers=max(1, len(thread_jobs))) as tpool:
        thread_futures = {
            name: tpool.submit(_timed_job(job)) for name, job in thread_jobs.items()
        }
        _drain_futures(thread_futures, raw, counts, timing, pool_label="")


# frob:ticket T-0581
def _run_combined_jobs(
    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]],
    process_jobs: dict[str, _ProcessJob],
    *,
    root: Path | None = None,
    max_process_workers: int | None = None,
) -> tuple[list[Violation], dict[str, int], dict[str, float]]:
    """Run `thread_jobs` on a `ThreadPoolExecutor` and `process_jobs`
    (the CPU-bound giants, T-0415/docs/audits/perf.md H3) on a
    `ProcessPoolExecutor` at the same time, so e.g. archgate and sys
    actually overlap instead of GIL-serializing on one shared pool. Merges
    results back via `_merge_canonical_order` so output stays deterministic
    regardless of which pool finishes a job first.

    T-0581: the process pool is created and its jobs SUBMITTED before the
    `ThreadPoolExecutor` opens, not nested inside it. The old ordering --
    `with ThreadPoolExecutor(...): ... with ProcessPoolExecutor(...): ...`
    -- forks worker processes while up to `len(thread_jobs)` gate threads
    were already running inside this same interpreter. A fork while a
    sibling thread holds an interpreter-internal lock (import lock,
    allocator arena lock, logging lock, etc.) copies that lock into the
    child in whatever state it was at fork time, but not the thread that
    would eventually release it -- any child code path that touches the
    same lock hangs forever. That exact interleaving produced a 6-hour CI
    hang and repeated local zombie process trees (T-0265 disclosure,
    T-0581's ticket body). `mp_context=spawn` is the LOAD-BEARING fix:
    this function IS called from worker threads (frob.check's
    _run_tasks_concurrently thread pool, the serve daemon's anyio worker
    threads), so at fork time sibling threads exist on the primary path
    and submit-order alone cannot prevent lock inheritance -- spawn starts
    each worker from a clean interpreter and is immune regardless of
    caller threading. Do NOT remove mp_context believing the
    submit-before-threads ordering suffices. Submitting to the process
    pool FIRST remains good hygiene (fewer of our own threads alive)
    rather than forking this one, so it carries no inherited lock state at
    all even if a future refactor reintroduces nested pools by accident.

    T-0767: this function is now a pure orchestrator -- pool CONSTRUCTION
    is owned by `_open_process_pool` and `_run_thread_jobs` so no single
    function contains both pool constructions, which discharges the
    (unwaivable-by-design) T-0695 `pool-inside-pool` structural advisory
    while preserving the T-0581 ordering exactly: create + submit the
    process pool first, then open the thread pool, then drain, then shut
    the process pool down. Do NOT inline either helper back here.

    T-1436: `max_process_workers` passes straight through to
    `_open_process_pool`'s own `max_workers` cap; see that docstring.

    T-1464: `root` passes straight through to `_open_process_pool`'s own
    `root` (the parse-artifact-cache env stamp); see that docstring.
    """
    counts: dict[str, int] = {}
    timing: dict[str, float] = {}
    raw: dict[str, tuple[Violation, ...]] = {}
    if not thread_jobs and not process_jobs:
        return [], counts, timing

    ppool: ProcessPoolExecutor | None = None
    process_futures: dict[str, Future[tuple[tuple[Violation, ...], float]]] = {}
    if process_jobs:
        ppool = _open_process_pool(
            process_jobs, root=root, max_workers=max_process_workers
        )
        process_futures = _submit_process_pool(ppool, process_jobs)

    try:
        _run_thread_jobs(thread_jobs, raw, counts, timing)
        if ppool is not None:
            _drain_futures(
                process_futures, raw, counts, timing, pool_label=" (process pool)"
            )
    finally:
        if ppool is not None:
            ppool.shutdown(wait=True)

    return _merge_canonical_order(raw), counts, timing


# frob:ticket T-1148
# frob:tests tests/test_gates.py::TestNativeAvailabilityGate.test_unimportable_native_short_circuits_run_gates_with_one_finding  # noqa: E501
def _native_unavailable_report(root: Path) -> GateReport | None:
    """T-1148: ONE `NATIVE001` `GateReport` naming every declared native
    that fails to import right now under `root` (`frob.strata.
    native_unavailable_warning`), or `None` when every declared native
    imports cleanly. `run_gates` returns this in place of its normal
    load-everything-then-run-every-gate pipeline the moment it is non-
    `None`: a broken native cascades into dozens of misattributed
    findings downstream (graph/design loading fails, so anchors and
    edges that would normally resolve through it look dangling instead --
    the 2026-07-28 incident's 43 spurious DRIFT002 "no candidates"
    errors, one per `design/frob.strata` node, when the real cause was a
    completely missing `strata_core`) -- reporting the ONE honest root
    cause here, before any of that runs, is strictly more useful than
    letting the cascade through. Imported inside the function body (not
    at module level) to avoid a `frob.gates` <-> `frob.strata` import
    cycle, the same discipline `_sys004_native_hint` already established
    for this exact pair of modules."""
    from frob.strata import native_unavailable_warning

    warning = native_unavailable_warning(root)
    if warning is None:
        return None
    _log.error("run_gates: %s", warning)
    return GateReport(
        violations=(
            Violation(
                rule="NATIVE001",
                severity=Severity.ERROR,
                file=str(root),
                line=0,
                message=f"NATIVE001: {warning}",
            ),
        ),
        waived=(),
        stats=GateStats(),
    )


#: T-1213: env-var opt-out for the auto-rebuild below -- set to skip
#: straight to the old reminder-only NATIVE001 behavior (e.g. a CI runner
#: that intentionally wants a stale/missing native to fail loudly rather
#: than pay a rebuild inline, or a sandbox with no toolchain at all where
#: even attempting the build wastes time before falling through anyway).
# frob:doc docs/modules/gates.md#native001-t-1148
# frob:ticket T-1501
NATIVE_AUTOREBUILD_DISABLE_ENV = "FROB_NO_NATIVE_AUTOREBUILD"


# frob:ticket T-1213
def _native_autorebuild_disabled(root: Path) -> bool:
    """True when T-1213's auto-rebuild should be SKIPPED: the
    `FROB_NO_NATIVE_AUTOREBUILD` env var is set (any non-empty value), or
    `root`'s own `frob.toml` declares top-level `natives_auto_rebuild =
    false`. Absence of either -- the common case -- means auto-rebuild
    stays ON, matching this ticket's default-on acceptance criteria."""
    if os.environ.get(NATIVE_AUTOREBUILD_DISABLE_ENV):
        return True
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception as exc:  # noqa: BLE001 -- best-effort probe, never fatal
        _log.debug("_native_autorebuild_disabled: unreadable frob.toml: %s", exc)
        return False
    return data.get("natives_auto_rebuild") is False


# frob:ticket T-1213
# frob:tests tests/test_natives.py::TestNativeAutorebuild.test_stale_native_triggers_autorebuild  # noqa: E501
# frob:tests tests/test_natives.py::TestNativeAutorebuild.test_missing_but_buildable_native_triggers_autorebuild  # noqa: E501
# frob:tests tests/test_natives.py::TestNativeAutorebuild.test_disabled_via_env_var_skips_autorebuild  # noqa: E501
# frob:tests tests/test_natives.py::TestNativeAutorebuild.test_build_failure_falls_through_to_native001  # noqa: E501
def _maybe_autorebuild_natives(root: Path) -> None:
    """T-1213: the fix for the recurring worktree-natives false-failure
    class this ticket's Description names -- a source-newer-than-artifact
    native (`frob.strata.stale_natives`) or an entirely unbuilt-but-
    buildable one (`frob.strata.unimportable_natives`, when a matching
    crate directory exists) used to only ever produce a NATIVE001
    reminder (T-0248/T-1148), leaving the actual rebuild to a human
    running `make core` by hand. This function attempts that rebuild
    itself, BEFORE `_native_unavailable_report` runs its own (still
    reminder-only) check -- disclosed loudly via `_log.warning` either
    way, per this ticket's acceptance criteria.

    Deliberately pure I/O with no return value: `_run_gates_bounded`
    calls this for its side effect (a freshly built native on disk) and
    then runs its EXISTING `_native_unavailable_report`/staleness checks
    unchanged -- if the rebuild succeeded, those checks now see a fresh
    artifact and report nothing; if it failed (T-0732's own documented
    no-toolchain case, `build_natives` returning a non-ok per-crate
    result, or an infra-level `Err`), they fall through to the ORIGINAL
    NATIVE001 fail-closed path exactly as before this ticket -- the
    guard this ticket's Description requires: never auto-build when the
    toolchain is absent, disclose and fail closed as today.

    A no-op (skips straight through) when `_native_autorebuild_disabled`
    says so, or when neither `stale_natives` nor `unimportable_natives`
    reports anything for `root` (the common, already-healthy case) --
    importing `frob.strata`/`frob.natives` here (not at module level)
    mirrors `_native_unavailable_report`'s own existing discipline for
    avoiding a `frob.gates` <-> `frob.strata` import cycle."""
    if _native_autorebuild_disabled(root):
        return
    from frob.strata import stale_natives, unimportable_natives

    stale = stale_natives(root)
    missing = unimportable_natives(root)
    if not stale and not missing:
        return

    stale_names = sorted({s.spec.name for s in stale})
    missing_names = sorted({s.name for s in missing})
    _log.warning(
        "run_gates: T-1213 auto-rebuild triggered (stale=%s, missing=%s)",
        stale_names,
        missing_names,
    )

    from frob.natives._build import build_natives

    built = build_natives(root)
    if built.is_err:
        _log.warning(
            "run_gates: T-1213 auto-rebuild could not run (%s) -- falling "
            "through to NATIVE001's own fail-closed reminder",
            built.danger_err,
        )
        return
    report = built.danger_ok
    if not report.ok:
        failed = sorted(r.name for r in report.results if not r.ok)
        _log.warning(
            "run_gates: T-1213 auto-rebuild ran but %s failed to build -- "
            "falling through to NATIVE001's own fail-closed reminder",
            failed,
        )
        return
    _log.warning(
        "run_gates: T-1213 auto-rebuild succeeded for %s",
        sorted(r.name for r in report.results),
    )


# frob:doc docs/modules/gates.md#public-api
# frob:doc docs/modules/gates.md#native001-t-1148
# frob:doc docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602  # noqa: E501
# frob:ticket T-0021
# frob:ticket T-0602
def run_gates(
    cfg: GateConfig, *, use_cache: bool = False
) -> Result[GateReport, GateError]:
    """Public entry point: `_run_gates_bounded` with no process-pool-size
    override (T-1436 -- kept as a thin, signature-stable wrapper so this
    function's own `frob:doc` contract in `docs/modules/gates.md`/
    `docs/modules/serve.md` needs no update just to add an internal-only
    sizing knob a handful of callers use)."""
    return _run_gates_bounded(cfg, use_cache=use_cache)


# frob:ticket T-1501
def _run_gates_bounded(
    cfg: GateConfig, *, use_cache: bool = False, max_process_workers: int | None = None
) -> Result[GateReport, GateError]:
    """Load everything once, then run the selected gates in parallel and
    merge -- `run_gates`'s actual implementation, plus one T-1436 addition:
    `max_process_workers`, private (no external caller contract), lets a
    caller that already knows it is CPU-competing with something else on
    the same box (currently only `frob.serve._tools.frob_check_delta`,
    which always runs inside the warm daemon process) cap
    `_open_process_pool`'s worker count below the normal `min(len(jobs),
    cpu_count())` bound. Every existing `run_gates` call site is
    unaffected -- this function's default (`None`) reproduces the exact
    pre-T-1436 behavior.

    T-0602: `use_cache=True` opts into per-gate dependency-tracked partial
    re-evaluation (`_gate_cache.evaluate_cacheable_gate`) for the closed
    `_CACHEABLE_GATES` allowlist -- every other gate, and every call site
    that leaves this at its `False` default (every existing `frob check`
    call), is unaffected: identical behavior to before this ticket. See
    `_gate_cache`'s module docstring for the full design and
    `docs/modules/serve.md` for which call sites opt in and why.

    T-1148: before anything else, check that every declared native
    extension actually imports (`_native_unavailable_report`) -- a broken
    native fails ONCE, honestly, here, instead of cascading into dozens of
    gates misattributing the same root cause to design/doc drift.

    T-1213: immediately before that check, `_maybe_autorebuild_natives`
    attempts to rebuild any native `_native_unavailable_report`/staleness
    would otherwise merely warn about -- a stale-source-vs-artifact or
    entirely-unbuilt-but-buildable native is rebuilt in place (disclosed
    loudly) so the very next line's check sees a fresh artifact instead
    of reporting NATIVE001, closing the worktree-natives false-failure
    class this ticket's Description names. NATIVE001 itself still fires,
    fail-closed, whenever the rebuild could not happen (no toolchain) or
    failed outright."""
    start_all = time.monotonic()
    selected = cfg.gates or _ALL_GATES
    _log.info(
        "run_gates: root=%s base=%s gates=%s use_cache=%s",
        cfg.root,
        cfg.base,
        sorted(selected),
        use_cache,
    )

    _repo_root_for_natives = _repo_root_for(Path(cfg.root))
    _maybe_autorebuild_natives(_repo_root_for_natives)
    native_report = _native_unavailable_report(_repo_root_for_natives)
    if native_report is not None:
        return Ok(native_report)

    inputs_result = _load_inputs(cfg)
    if inputs_result.is_err:
        return Err(inputs_result.danger_err)
    st = inputs_result.danger_ok

    thread_jobs, process_jobs, skipped = _build_jobs(selected, st, use_cache=use_cache)
    report = _assemble_gate_report(
        cfg,
        st,
        thread_jobs,
        process_jobs,
        skipped,
        start_all,
        max_process_workers=max_process_workers,
    )
    return Ok(report)


#: T-1464: a SEPARATE db file from `_CACHE_REL` (`.frob/cache.db`), even
#: though `store_parsed_artifact`/`load_parsed_artifact` live in the same
#: `frob.graph.cache` module and share its schema/fingerprint machinery.
#: Every `ProcessPoolExecutor` gate worker (perf/clones/dead_symbols/arch/
#: sys) opens its OWN connection to whichever file this points at; pointed
#: at `.frob/cache.db` itself, that piled N extra concurrent connections
#: onto the SAME file `frob.graph.build_graph`'s own `store_file_data` was
#: already writing under its own T-1423 contention budget, and measurably
#: exhausted it (`database is locked` on `store_file_data`, unrelated to
#: this cache's own writes -- a T-1464 incident, not a T-1423 regression).
#: A dedicated file isolates the new write load from the pre-existing one.
_PARSE_ARTIFACT_CACHE_REL = Path(".frob") / "parse-artifacts.db"


def _parse_artifact_cache_path(root: Path) -> Path:
    """`root`'s resolved `.frob/parse-artifacts.db` path (T-1464) --
    deliberately NOT `.frob/cache.db` (see `_PARSE_ARTIFACT_CACHE_REL`'s
    comment); `frob.lang.PARSE_ARTIFACT_CACHE_ENV` stamps this path so
    every worker opens the same persistent parse-artifact store."""
    return (root / _PARSE_ARTIFACT_CACHE_REL).resolve()


def _assemble_gate_report(
    cfg: GateConfig,
    st: _GateInputs,
    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]],
    process_jobs: dict[str, _ProcessJob],
    skipped: list[str],
    start_all: float,
    *,
    max_process_workers: int | None = None,
) -> GateReport:
    """Run `thread_jobs`/`process_jobs` (T-0415), fold in the WAIVE001/
    WAIVE002/DSL001 self-checks, apply waivers and severity overrides, and
    log the run's final tally.

    T-1436: `max_process_workers` passes straight through to
    `_run_combined_jobs`'s own `max_process_workers`."""
    all_violations: list[Violation] = [
        *_waive001_violations(st.snapshot),
        *_waive002_violations(st.snapshot, st.rule_ids),
        # T-0753: `until=` expiry needs no assembled violation set (it only
        # reads the waive edges' own attrs), so it runs alongside the other
        # up-front WAIVE00*/DSL001 self-checks.
        *_waive005_violations(st.snapshot, current_date=date.today().isoformat()),
        # T-0779: stale-waiver detection needs only the snapshot's own
        # waive edges plus the merged ticket queue -- no assembled
        # violation set dependency, so it runs alongside the other WAIVE00*
        # self-checks rather than after job_violations like WAIVE003/004.
        *waive006_gate(st.repo_root, st.snapshot, st.queue),
        # T-0808: same dependency shape as WAIVE006 (snapshot waive edges
        # + merged ticket queue only), so it runs alongside it.
        *waive007_gate(st.repo_root, st.snapshot, st.queue),
        *_dsl001_violations(st.snapshot),
    ]
    job_violations, counts, timing = _run_combined_jobs(
        thread_jobs,
        process_jobs,
        root=st.repo_root,
        max_process_workers=max_process_workers,
    )
    counts["waive"] = len(all_violations)
    all_violations.extend(job_violations)
    # T-0470: WAIVE003 needs the full assembled violation set (it re-runs
    # `_match_waiver` per package-scoped violation to see how many distinct
    # packages one waiver reaches), so it runs after `job_violations` is
    # folded in, not alongside the other WAIVE00* self-checks above.
    all_violations.extend(_waive003_violations(tuple(all_violations), st.snapshot))
    # T-0753: WAIVE004 (zero-findings stale-waiver detection) needs the same
    # full pre-waiver violation set WAIVE003 does, for the same reason --
    # "how many findings does this waiver's rule produce right now" can only
    # be answered once job_violations are folded in.
    # T-1133: only trustworthy on a full, unscoped run -- a `--only` gate
    # selection (`cfg.gates`) or a `--ticket`-scoped diff (`cfg.ticket`)
    # both make "0 findings" indistinguishable from "the gate/diff-scope
    # that would have produced a match simply did not run this time".
    all_violations.extend(
        _waive004_violations(
            tuple(all_violations),
            st.snapshot,
            st.rule_ids,
            full_unscoped_run=not cfg.gates and cfg.ticket is None,
        )
    )
    # T-0978: `frob:secret-fake` stays a reserved, graph-invisible marker
    # verb (T-0157 -- `frob.graph.dsl._RESERVED_MARKER_VERBS`), so it never
    # becomes a real `frob:waive` `Edge` the graph-edge `_waive004_
    # violations` above can iterate. `fake_marker_staleness_gate` is the
    # same zero-findings staleness check reimplemented at the GATE level
    # (it re-scans tracked files for the marker's own reason-bearing sites
    # and checks each one still trips a real secret-pattern hit) -- folded
    # in here, right after the graph-edge WAIVE004 pass, so both sources
    # present as one `WAIVE004` rule to a caller. Independent of
    # job_violations (it does its own tracked-file scan), so it does not
    # need to run before/after any particular job like WAIVE003/004 above.
    all_violations.extend(fake_marker_staleness_gate(st.root))

    kept, waived = _apply_waivers(tuple(all_violations), st.snapshot)
    kept = _apply_severity_overrides(kept, cfg.root)
    stats = GateStats(counts=counts, timing_s=timing, skipped=tuple(skipped))
    _log.info(
        "run_gates: done in %.3fs, %d kept, %d waived, skipped=%s",
        time.monotonic() - start_all,
        len(kept),
        len(waived),
        skipped,
    )
    return GateReport(violations=kept, waived=waived, stats=stats)


__all__ = [
    "CoverageData",
    "CoverageError",
    "DebtEntry",
    "DecisionError",
    "DeprecatedEntry",
    "FmtChange",
    "FmtReport",
    "GateConfig",
    "GateError",
    "GateReport",
    "GateStats",
    "Invariant",
    "InvariantError",
    "PreworkSweep",
    "RatchetEntry",
    "RatchetError",
    "RatchetPool",
    "Severity",
    "SystemSpec",
    "TestPolicy",
    "Violation",
    "WaiverRef",
    "active_ticket",
    "affect_drift_gate",
    "arch_gate",
    "clear_ratchet_entry",
    "coverage_gate",
    "delta_violations",
    "drift_gate",
    "exclude_hazard_gate",
    "fake_marker_staleness_gate",
    "fmt_gate",
    "format_paths",
    "inv003_gate",
    "inv004_gate",
    "inv006_gate",
    "invalidate_gate_cache",
    "inv007_violations",
    "inv008_violations",
    "invariant_gate",
    "known_gate_rule_ids",
    "_UNWAIVABLE_RULES",
    "_match_waiver",
    "SCOPED_RUN_FLAKY_RULE_IDS",
    "_waive006_binding_ticket_refs",
    "_waive006_comment_violations",
    "_waive006_strata_violations",
    "_waive007_comment_violations",
    "_waive007_is_exempt_dangling_ref",
    "_waive007_strata_violations",
    "coverage_lock_diff",
    "is_baseline_stale",
    "load_baseline",
    "load_coverage",
    "load_coverage_lock",
    "load_invariants",
    "mutation_evidence_violations",
    "bug_repro_violations",
    "compliance_gate",
    "cve_fingerprint_scan_gate",
    "debt_gate",
    "decisions_gate",
    "deprecated_gate",
    "deprecated_current_references",
    "doclink_gate",
    "docanchor_gate",
    "docstatus_gate",
    "docmake_gate",
    "dup_gate",
    "list_debt",
    "list_deprecated",
    "evidence_covers_scope",
    "fuzz_gate",
    "lang_conformance_gate",
    "perf_gate",
    "pii_structural_gate",
    "project_lang_conformance_gate",
    "protocol_summary_gate",
    "release_gate",
    "prework_gate",
    "record_prework",
    "registry_gate",
    "render_lint_gate",
    "run_gates",
    "scope_digest",
    "scope_gate",
    "secrets_gate",
    "suppress001_gate",
    "SuppressionDialect",
    "suppression_dialects",
    "snapshot_ratchet",
    "stamp_baseline",
    "stamp_coverage",
    "ticket_lease_pin",
    "sweep_ticket",
    "sys_gate",
    "test_gate",
    "violation_fingerprint",
    "waive006_gate",
    "waive007_gate",
    "walk_lint_gate",
    "write_coverage_lock",
]
