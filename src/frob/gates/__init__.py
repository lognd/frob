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
import difflib
import fnmatch
import functools
import hashlib
import os
import re
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import TypeVar

from pydantic import ValidationError
from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

from frob.excludes import is_excluded, is_test_file, iter_files, load_exclude_globs
from frob.gates._arch import arch_gate
from frob.gates._baseline import (
    delta_violations,
    is_baseline_stale,
    load_baseline,
    stamp_baseline,
    violation_fingerprint,
)
from frob.gates._coverage import load_coverage, load_stamp, stamp_coverage
from frob.gates._cve_fingerprint_scan import cve_fingerprint_scan_gate
from frob.gates._docblocks import doc004_gate
from frob.gates._exclude_hazard import exclude_hazard_gate
from frob.gates._models import (
    CoverageData,
    CoverageError,
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
from frob.gates._pii_structural import pii_structural_gate
from frob.gates._prework import load_prework, record_prework, sweep_ticket
from frob.gates._refs import ref_gate
from frob.gates._registry_exhaustiveness import registry_gate
from frob.gates._secrets import secrets_gate
from frob.gates._walk_lint import walk_lint_gate
from frob.gates.decisions import DecisionError
from frob.gates.invariants import (
    Invariant,
    InvariantError,
    find_exclusivity_claims,
    find_normative_claims,
    load_invariants,
)
from frob.gitio import Diff, Hunk, current_branch, run_argv, working_diff
from frob.graph import (
    Edge,
    EdgeKind,
    GraphSnapshot,
    build_graph,
    dedupe_slug,
    edges_from,
    slugify,
)
from frob.graph._generated import is_generated_source
from frob.graph._models import LockFile
from frob.graph.lock import drift as _graph_drift
from frob.graph.lock import load_lock
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile, RawComment, RawSymbol
from frob.lang._walk_rust import _MACRO_SYMBOL_SUFFIX
from frob.logging import get_logger
from frob.testing import CollectedTests, collect_python_tests, collect_rust_tests
from frob.tickets import Ticket, TicketQueue, TicketState, closed_ticket_ids, load_queue
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    Priority,
    is_cmd_evidence,
    matches_collected,
    scope_matches,
)
from frob.tickets._provisional import is_draft_id, on_default_branch
from frob.tickets._store import _parse_ledger as _tickets_parse_ledger
from frob.tickets._store import load_all as _tickets_load_all
from frob.tickets._store import load_archive as _tickets_load_archive

_log = get_logger(__name__)

_OPEN_STATES = frozenset(
    s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
)
_TODO_RE = re.compile(r"\b(TODO|FIXME)\b")


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
    binding correctly in both cases -- proven directly, not assumed)."""
    if base_node_id in node_ids:
        return True
    prefix = f"{base_node_id}["
    return any(node_id.startswith(prefix) for node_id in node_ids)


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


# frob:ticket T-0298
def _is_path_level_evidence(evidence: str) -> bool:
    """True if `evidence` names a file or directory rather than a single
    test node (`path::qualname`) -- no `::` at all, e.g. `tests/test_vet.py`
    or `tests/unit/deploy`."""
    return "::" not in evidence


# frob:ticket T-0298
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
# evidence for -- collect_python_tests only spawns pytest and
# collect_rust_tests only spawns cargo, so a ts/c/cpp `frob:tests` edge can
# never have its `src` land in `tests.node_ids`, no matter which file the
# directive itself lives in (T-0090). Rust was removed from this set by
# T-0092: `collect_rust_tests` gives rust real execution evidence via
# `tests.node_ids` (the first branch of `_valid_edges` below), so a rust
# `frob:tests` src no longer needs (or should use) the structural fallback.
_NATIVE_TEST_EXTENSIONS = frozenset(
    {".ts", ".tsx", ".c", ".h", ".cpp", ".hpp", ".cc", ".hh"}
)


def _is_native_test_src(src: str) -> bool:
    """True if `src`'s file extension has no execution-based test collector
    (see `_NATIVE_TEST_EXTENSIONS`); pytest is the only one frob runs."""
    path = src.split("::", 1)[0]
    return PurePosixPath(path).suffix.lower() in _NATIVE_TEST_EXTENSIONS


def _is_native_test_symref(src: str) -> bool:
    """True if `src`'s qualname follows a test-code convention this module
    already trusts elsewhere: a `tests` module/namespace segment (rust's
    `#[cfg(test)] mod tests { ... }`, mirroring `is_test_file`'s "tests" dir
    check) or a `test_`/`_test` leaf name (the C/C++/TS convention, mirroring
    `_is_test_path`'s python check). Extension alone (`_is_native_test_src`)
    only says "no execution collector exists"; this says "and it actually
    looks like test code" -- required together so a plain `frob:tests`
    directive on a non-test rust/ts/c/cpp file (e.g. the target's own
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
    """Edges whose `src` is a collected pytest or cargo node id (real execution
    evidence, `_symref_to_nodeid`), or -- for a language frob still has no
    execution-based test collector for (ts/c/cpp, T-0090) -- a `src` that both
    looks like test code (`_is_native_test_symref`) and resolves to a real
    bound symbol in `snapshot`.

    The comment DSL binds a `frob:tests` directive to its enclosing/following
    symbol regardless of which file it lives in relative to its target
    (`frob.graph.dsl.parse_directives`), so a directive whose src is a genuine
    ts/c/cpp test function is structurally authoritative the moment it exists;
    frob just cannot (yet) prove the test actually ran the way it now can for
    python (`collect_python_tests`) and rust (`collect_rust_tests`, T-0092).
    `snapshot` is optional so existing callers that only ever see python
    evidence are unaffected.

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
    return (
        snapshot is not None
        and _is_native_test_src(e.src)
        and _is_native_test_symref(e.src)
        and e.src in snapshot.symbols
    )


# frob:ticket T-0307
def _case_count(valid_edges: list[Edge], tests: CollectedTests) -> int:
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
    at all (the ts/c/cpp structural fallback in `_valid_edges`, which has
    no pytest/cargo evidence to expand) still counts as exactly one case,
    matching its previous `len(valid_edges)` contribution.
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
        prefix = f"{base}["
        matches = sum(
            1
            for node_id in tests.node_ids
            if node_id == base or node_id.startswith(prefix)
        )
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
    return sum(
        1 for node in tests.node_ids if token.search(_snake(node.rsplit("::", 1)[-1]))
    )


def _waive_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every valid `frob:waive` edge in the snapshot (dsl.py already rejects a
    waive directive missing `reason=...` as a MalformedDirective, so every
    surviving WAIVE edge here is guaranteed to carry a reason)."""
    return tuple(e for e in snapshot.edges if e.kind == EdgeKind.WAIVE)


def _waivers_by_rule(snapshot: GraphSnapshot) -> dict[str, list[Edge]]:
    """Index WAIVE edges by their target rule id for O(1) rule lookup."""
    index: dict[str, list[Edge]] = {}
    for edge in _waive_edges(snapshot):
        index.setdefault(edge.target, []).append(edge)
    return index


def _waive001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """WAIVE001: a `frob:waive` directive missing `reason=...` -- surfaced from
    frob.graph's MalformedDirective list, since frob.graph.dsl already refuses
    to turn such a line into an edge."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:waive" not in md.reason:
            continue
        _log.debug("WAIVE001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="WAIVE001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=(
                    f'WAIVE001: {md.file}:{md.line} frob:waive missing reason="..."; '
                    f"add a reason attribute or remove the waiver"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0101
# Every rule id any Violation-producing gate can emit. `frob:waive` only
# ever suppresses entries in the GateReport's `violations` tuple (see
# `_apply_waivers` below) -- a waiver targeting anything outside this set
# can never match, so WAIVE002 treats that as the definition of
# "unwaivable channel" rather than hardcoding a channel allowlist.
_KNOWN_GATE_RULES = frozenset(
    {
        "COV001",
        "COV002",
        "COV003",
        "COV004",
        "COV005",
        # T-0483: `frob:tests` call-graph reachability (COV006) and
        # a `frob:doc` anchor bound to a private helper (COV007).
        "COV006",
        "COV007",
        # T-0504: class-directive placement lint (a `frob:` directive that
        # class-falls-back but plausibly missed a nearby real symbol).
        "PLACE001",
        "DRIFT001",
        "DRIFT002",
        "SCOPE001",
        "PRE001",
        "INV001",
        "INV002",
        "INV003",
        "INV004",
        "TEST001",
        "TEST002",
        "TEST003",
        "TEST004",
        "TEST005",
        "TEST006",
        "TEST007",
        "TEST008",
        "TEST009",
        "TEST010",
        "TEST011",
        "TODO001",
        "TODO002",
        "WAIVE001",
        "WAIVE002",
        # T-0470: over-broad package-prefix waiver reach.
        "WAIVE003",
        "DEC001",
        "DEC002",
        "REL001",
        "DOC001",
        "DOC002",
        "DOC003",
        "DUP001",
        "DUP002",
        "FUZZ001",
        "FUZZ002",
        "FUZZ003",
        "PERF001",
        "PERF002",
        "PERF003",
        "PERF004",
        "PERF005",
        "PERF006",
        "PERF007",
        "SYS001",
        "SYS002",
        "SYS003",
        "SYS004",
        "SEC001",
        "SEC002",
        "SEC003",
        "TICK001",
        "TICK002",
        # T-0409: ledger-hygiene gate (frob.gates.tickets_gate's
        # _tick003_stale_archive) -- too many closed tickets sitting
        # un-archived in the active tickets.md ledger.
        "TICK003",
        # T-0411: queue-health/priority-rot gate (frob.gates.tickets_gate's
        # _tick004_queue_rot) -- a queued/planned ticket past its
        # priority-specific rot-day threshold.
        "TICK004",
        "PII010",
        "SEC110",
        # T-0289: long-function is the one frob-arch category channeled into
        # a real gate Violation (see frob.gates._arch's module docstring for
        # why only this one, not the whole ArchCategory surface).
        "ARCH001",
        # T-0396: anti-orphan file-reference gate (frob.gates._refs).
        "REF001",
        "REF002",
        "REF003",
        # T-0343: registry exhaustiveness drift-lock
        # (frob.gates._registry_exhaustiveness).
        "REG001",
        "REG002",
        "REG003",
        "REG004",
        "REG005",
        # T-0436: unbound/stale fenced-code-block doc-drift heuristic
        # (frob.gates._docblocks).
        "DOC004",
        # T-0471: unpruned filesystem traversal (frob.gates._walk_lint).
        "WALK001",
        # T-0465: .git/info/exclude entry shadowing tracked source
        # (frob.gates._exclude_hazard).
        "EXCL001",
        # T-0439: CVE code-smell needle/fingerprint pattern-scan
        # (frob.gates._cve_fingerprint_scan).
        "SEC-CVE-FINGERPRINT-001",
    }
)


# frob:ticket T-0499
# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_returns_known_rule_id
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_is_frozenset
def known_gate_rule_ids() -> frozenset[str]:
    """Return every rule id a gate can emit, for strata `caught_by`
    resolution to recognize rule-id-shaped references (e.g. THREAT006's
    and COMPLIANCE004's `known_rule_ids` param) instead of treating them
    as unresolved by default.
    """
    return _KNOWN_GATE_RULES


# frob:ticket T-0148
# TEST008 (coverage.xml carried data but zero of it joined to a known repo
# path) is excluded from `_match_waiver` by construction, not merely by
# convention -- it exists specifically to make a silent-death coverage
# misconfiguration loud in EVERY sibling repo this gate runs in, so a
# `frob:waive TEST008 reason="..."` sitting in one repo's tree must never
# quietly suppress it there. `frob.toml`'s `[gates.severity]` override
# table is a different, explicit, per-repo mechanism (visible in the
# frob.toml diff, not a buried code comment) and is NOT blocked here --
# only the same-repo `frob:waive` directive path is.
#
# frob:ticket T-0157
# SEC003 (`frob.gates._secrets`): a live Stripe SECRET key (`sk_live_...`)
# or a private-key PEM header tracked in the repo. Written decision (the
# ticket asked for one explicitly): these two get the same unwaivable
# treatment as TEST008, NOT the broader `SEC001` rule id that the rest of
# the secrets-scan pattern table reports under. `SEC001` deliberately stays
# waivable -- it also carries lower-confidence, genuinely disputable
# findings (a JWT that may be a public ID token, Plaid's context-gated
# heuristic, Stripe TEST-mode keys) where a written `frob:waive` reason is
# the correct, honest outcome, not a workaround. A live Stripe secret key
# or a PEM private-key header have no such legitimate "yes, intentionally"
# case -- unlike a JWT, there is no reading of either shape that is
# supposed to be public, so silencing one with a comment is never correct
# and is now structurally impossible, the same way TEST008 makes a silent
# coverage misconfiguration impossible.
#
# frob:ticket T-0162
# TICK001/TICK002 join TEST008 for the identical reason: they exist
# specifically to make the T-0162 ticket-id collision invariant's failure
# modes loud. TICK001 (duplicate id active+archive) can already only be
# reached if ledger loading itself becomes more permissive than today's
# hard Err, and TICK002 (a draft id reaching the default branch) is exactly
# the "finalize step got skipped" failure this whole mechanism exists to
# catch -- a `frob:waive TICK002 reason="..."` sitting in the tree would
# let a live collision risk sit there quietly forever. See the decision
# record in docs/modules/tickets.md#decision-record-t-0162.
# T-0465: EXCL001 joins the same unwaivable set -- a `frob:waive` comment
# lives in a source file, but the violation's own "file" is
# `.git/info/exclude` itself; there is nowhere honest to attach a waiver,
# and the remedy is always the same (remove the entry, or use a
# genuinely untracked path). See docs/modules/gates.md#excl001-t-0465.
_UNWAIVABLE_RULES = frozenset({"TEST008", "SEC003", "TICK001", "TICK002", "EXCL001"})


def _unwaivable_channel_rules() -> frozenset[str]:
    """Rule/category ids from tool channels `frob:waive` can never reach.

    T-0101 decision (documented in docs/modules/gates.md#waive-boundary):
    honoring waivers in the `frob-arch` check stage would mean threading
    the waiver-matching machinery into `frob.check`'s Diagnostic pipeline
    (`analyze_project` produces `ArchSuggestion`s, never `Violation`s) --
    a bigger surface change than a WARN justifies today. Instead, a waiver
    that names one of `frob.arch`'s categories is flagged as ineffective
    rather than silently doing nothing.

    T-0289 narrows this: `long-function` is EXCLUDED here because
    `frob.gates._arch.arch_gate` now channels it into real `Violation`s
    (rule id `ARCH001`, not the bare category name `long-function`) that
    DO go through `_apply_waivers` -- a `frob:waive long-function
    reason="..."` still can't match anything (the rule id is `ARCH001`,
    not the category string), so it correctly stays flagged here, but the
    correct directive (`frob:waive ARCH001 reason="..."`) is no longer
    ineffective. Every other arch category is unchanged.
    """
    from typing import get_args

    from frob.arch._models import ArchCategory

    return frozenset(get_args(ArchCategory)) - {"long-function"}


def _waive002_violations(
    snapshot: GraphSnapshot, rule_ids: frozenset[str]
) -> tuple[Violation, ...]:
    """WAIVE002: a `frob:waive` targets a rule id that can never be matched
    by `_apply_waivers` -- neither a known gate rule nor a loaded policy
    rule id. T-0101: this is the "unwaivable channel" case made loud
    instead of a silent no-op; `rule_ids` is the run's loaded policy rule
    ids, since those are dynamic (frob.toml-defined) and not known statically.
    """
    known = _KNOWN_GATE_RULES | rule_ids
    if _waive_edges(snapshot) == ():
        return ()
    arch_categories = _unwaivable_channel_rules()
    return tuple(
        _waive002_violation_for(edge, arch_categories)
        for edge in _waive_edges(snapshot)
        if edge.target not in known
    )


def _waive002_violation_for(edge: Edge, arch_categories: frozenset[str]) -> Violation:
    """The single WAIVE002 `Violation` (already logged) for one ineffective
    `frob:waive` edge -- distinguishing the frob-arch-category case (whose
    stage never consults `frob:waive` at all) from an unrecognized rule id."""
    file = edge.src.split("::", 1)[0]
    if edge.target in arch_categories:
        detail = (
            f"'{edge.target}' is a frob-arch category, not a gates rule id; "
            f"the frob-arch check stage does not consult frob:waive"
        )
    else:
        detail = f"'{edge.target}' is not a recognized gate or policy rule id"
    _log.warning(
        "WAIVE002: %s waives %s, which is ineffective: %s",
        edge.src,
        edge.target,
        detail,
    )
    return Violation(
        rule="WAIVE002",
        severity=Severity.WARN,
        file=file,
        line=0,
        message=(
            f"WAIVE002: frob:waive on {edge.src} targeting "
            f"'{edge.target}' is ineffective -- {detail}"
        ),
    )


# frob:ticket T-0470
def _waive003_violations(
    violations: tuple[Violation, ...], snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """WAIVE003: a single `frob:waive` edge on a package-scoped rule
    (`_PACKAGE_SCOPED_RULES`) that reaches MORE THAN ONE distinct violated
    package/system id via `_match_waiver`'s directory-prefix fallback.

    A waiver sitting in one file under `src/frob` matches every TEST003/
    TEST007 violation for every ancestor package prefix of that file's own
    path (`src/frob`, `src/frob/gates`, ...) simultaneously -- the same
    directive silently suppresses findings the author most likely never
    saw, let alone intended to waive, because they were reasoning about
    their own immediate package, not its ancestors. WARN severity: this is
    a scope-hygiene nudge (split into one waiver per package, or move each
    to its own package), not a correctness bug on its own.
    """
    waivers_by_rule = _waivers_by_rule(snapshot)
    reach: dict[tuple[str, str], set[str]] = {}
    for violation in violations:
        if violation.rule not in _PACKAGE_SCOPED_RULES:
            continue
        match = _match_waiver(violation, waivers_by_rule)
        if match is None:
            continue
        reach.setdefault((violation.rule, match.origin), set()).add(violation.file)
    out: list[Violation] = []
    for (rule, origin), files in reach.items():
        if len(files) <= 1:
            continue
        file, _, line_text = origin.rpartition(":")
        line = int(line_text) if line_text.isdigit() else 0
        packages = ", ".join(sorted(files))
        _log.warning(
            "WAIVE003: %s frob:waive %s reaches %d packages: %s",
            origin,
            rule,
            len(files),
            packages,
        )
        out.append(
            Violation(
                rule="WAIVE003",
                severity=Severity.WARN,
                file=file or origin,
                line=line,
                message=(
                    f"WAIVE003: {origin} frob:waive {rule} matches {len(files)} "
                    f"distinct packages ({packages}) via directory-prefix reach; "
                    f"likely broader than intended -- split into one waiver per "
                    f"package"
                ),
            )
        )
    return tuple(out)


# frob:ticket T-0504
# PLACE001 was first prototyped as "distance from the class's own span
# start" and DELIBERATELY DROPPED (T-0470) before landing: that heuristic
# fired on this repo's own widespread, legitimate idiom of per-field
# `frob:waive`/`frob:ticket` comments documenting one field deep inside a
# large pydantic config class (e.g. `src/frob/app/config.py`'s
# `AppConfig`, `frob:waive SCOPE001` at line 212, 150+ lines past the
# class's `class AppConfig:` line) -- fields are not `RawSymbol`s (only
# FUNCTION/METHOD/CLASS/CONST/TYPE are), so a directive above one always
# falls back to the enclosing class by construction, and doing so far
# from the class top is completely intentional there, not mis-scoped.
#
# T-0504 replaces that raw-distance signal with the materially different
# one this comment's own predecessor named as the real fix: does a
# nearby REAL symbol exist that the directive plausibly SHOULD have
# bound to via `following` but didn't reach, with nothing but blank
# lines/comments/decorators between the directive and that symbol? The
# per-field idiom always has genuine field-assignment CODE in that gap
# (the very thing that makes it a field and not a stray comment), so it
# is excluded by construction rather than by distance -- see
# `_place001_missed_symbol`'s docstring for the full argument and
# `TestPlace001Gate` for both the non-vacuous positive (a directive
# separated from its intended `def` by one blank line too many) and the
# AppConfig-shaped negative (a directive above a field, real code before
# the next real method).
_PLACE001_LOOKAHEAD = 10


# frob:ticket T-0504
def _place001_missed_symbol(
    comment: RawComment,
    symbols: tuple[RawSymbol, ...],
    lines: list[str],
) -> RawSymbol | None:
    """The nearby REAL symbol (within `_PLACE001_LOOKAHEAD` lines) that a
    class-fallback-bound `frob:` directive plausibly intended but missed
    via `_find_following_symbol`'s narrower window -- `None` if no such
    symbol exists, or if genuine code (anything other than a blank line,
    a `#`/`//` comment, or a decorator line) sits between the directive
    and the candidate.

    That "genuine code in between" check is the whole soundness argument
    (T-0504): the only way `following` can miss a REAL symbol that is
    still close by is a run of blank lines, stacked comments, or
    decorators wider than `_FOLLOWING_SYMBOL_WINDOW` -- none of which is
    itself an intervening obligation the directive could instead belong
    to. The per-field pydantic idiom this ticket must NOT fire on always
    has actual field-assignment code in that gap (that is what makes it
    a field), so it can never produce a candidate here regardless of how
    close or far the class's next real method sits.
    """
    end = comment.span[1]
    candidates = [
        sym for sym in symbols if end < sym.span[0] <= end + _PLACE001_LOOKAHEAD
    ]
    if not candidates:
        return None
    candidate = min(candidates, key=lambda sym: sym.span[0])
    for lineno in range(end + 1, candidate.span[0]):
        if lineno - 1 >= len(lines):
            break
        stripped = lines[lineno - 1].strip()
        if stripped == "" or stripped.startswith(("#", "//", "@")):
            continue
        return None
    return candidate


# frob:ticket T-0504
def _place001_bindings(
    comments: tuple[RawComment, ...], path: str
) -> dict[int, tuple[str, bool]]:
    """`comment_id -> (resolved_src, via_following)` for every comment in
    `comments`, mirroring `frob.graph.dsl._resolve_block_srcs`'s exact
    stacked-comment-propagation algorithm (order, carry state) but ALSO
    tagging whether the binding was reached via a `following` match
    (direct, or propagated backward from a later comment's own resolved
    `following` in the same contiguous block, T-0313) versus a genuine
    `enclosing`/bare-path fallback.

    This distinction is the entire soundness argument for PLACE001: a
    `frob:doc`/`frob:ticket` comment placed directly above `class Foo:`
    resolves via `following` straight to `Foo` (correct and intentional,
    `via_following=True`) even though `Foo` is a CLASS -- checking only
    "did this resolve to a class" (as `_resolve_block_srcs`'s plain
    output would tempt) cannot tell that apart from a directive genuinely
    stuck at the class-fallback because it sits somewhere INSIDE the
    class body with no reachable `following` target at all
    (`via_following=False`). Only the latter is what T-0504's placement
    check should ever consider.
    """
    from frob.graph.dsl import _enclosing_src

    order = sorted(range(len(comments)), key=lambda i: comments[i].span[0])
    resolved: dict[int, tuple[str, bool]] = {}
    carry_start: int | None = None
    carry_src: str | None = None
    for idx in reversed(order):
        comment = comments[idx]
        if comment.following is not None:
            src = f"{path}::{comment.following}"
        elif carry_src is not None and comment.span[1] + 1 == carry_start:
            src = carry_src
        else:
            resolved[idx] = (_enclosing_src(comment, path), False)
            carry_start = None
            carry_src = None
            continue
        resolved[idx] = (src, True)
        carry_start = comment.span[0]
        carry_src = src
    return resolved


# frob:ticket T-0504
def _place001_file(root: Path, file: str) -> tuple[Violation, ...]:
    """PLACE001 findings for one file: a `frob:` directive whose fully
    resolved binding (`_place001_bindings`, the same stacked-comment-aware
    resolution `parse_directives` itself uses) is a genuine class
    FALLBACK (`via_following=False`, not a directive that correctly
    resolved via `following` straight to a class it precedes), where
    `_place001_missed_symbol` finds a real symbol the directive plausibly
    should have reached instead.

    Re-parses `file` directly (root-relative, like `_cov006`/`_cov005`)
    rather than reusing `GraphSnapshot` -- the snapshot only carries
    already-resolved `Edge`s, not the per-comment `following`/`enclosing`
    detail this check needs.
    """
    from frob.lang import parse_file

    result = parse_file(root / file)
    if result.is_err:
        return ()
    parsed = result.danger_ok
    try:
        lines = (root / file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.warning("PLACE001: could not read %s: %s", file, exc)
        return ()
    symbol_by_qualname = {sym.qualname: sym for sym in parsed.symbols}
    resolved = _place001_bindings(parsed.comments, file)
    violations: list[Violation] = []
    for comment_id, comment in enumerate(parsed.comments):
        if not comment.text.startswith("frob:"):
            continue
        src, via_following = resolved[comment_id]
        if via_following:
            continue
        _prefix, sep, qualname = src.partition("::")
        if not sep:
            continue
        enclosing_sym = symbol_by_qualname.get(qualname)
        if enclosing_sym is None or enclosing_sym.kind != SymbolKind.CLASS:
            continue
        missed = _place001_missed_symbol(comment, parsed.symbols, lines)
        if missed is None:
            continue
        _log.debug(
            "PLACE001: %s:%s directive class-falls-back to %s, missed %s",
            file,
            comment.span[0],
            qualname,
            missed.qualname,
        )
        violations.append(
            Violation(
                rule="PLACE001",
                severity=Severity.WARN,
                file=file,
                line=comment.span[0],
                message=(
                    f"PLACE001: {file}:{comment.span[0]} frob: directive "
                    f"falls back to enclosing class {qualname!r}, but "
                    f"{missed.qualname!r} starts at line {missed.span[0]} "
                    f"with nothing but blank lines/comments/decorators in "
                    f"between -- likely intended for that symbol; move "
                    f"the directive within the following-window, or "
                    f"confirm the class binding is intentional"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0504
def _place001(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PLACE001 (advisory): a `frob:` directive that class-falls-back
    (`_place001_file`) instead of reaching a real, nearby symbol via
    `following` -- a likely mis-scoped directive, not raw distance from
    the class's own span start (T-0470's dropped prototype; see the
    comment above `_PLACE001_LOOKAHEAD` for the full history).

    WARN severity: best-effort, name/position-based (same tier as
    COV006) -- a finding is a prompt to double check, not proof the
    directive is wrong.
    """
    files = sorted({symref.split("::", 1)[0] for symref in snapshot.symbols})
    violations: list[Violation] = []
    for file in files:
        violations.extend(_place001_file(root, file))
    return tuple(violations)


# _match_waiver has three matching modes, chosen by `violation.symref`/
# `violation.rule` -- this comment (not the docstring) carries the
# historical detail so frob-arch's long-function line count reflects
# the code, not the explanation:
#
# - `violation.symref is not None` (currently only TEST005's per-symbol
#   branch-coverage check): the violation is about exactly one symbol,
#   so only an EXACT `waiver.src == violation.symref` counts -- a
#   `frob:waive` placed above a *different* symbol, or bare at file
#   top, does not match. Without this, placement above a specific
#   symbol is cosmetic: `frob.graph.dsl`'s `_enclosing_src` still binds
#   a `path::qualname` edge, but the old file-prefix comparison below
#   stripped the `::qualname` back off before comparing, so one
#   directive anywhere in a file silently waived every violation of
#   that rule in the whole file (the blanket-waiver bug T-0148's
#   review caught empirically: 102 file-top waivers absorbing 195
#   distinct findings).
# - `violation.symref is None` (every other rule, plus TEST005's own
#   per-module line-coverage and per-system checks, which have no
#   single symbol to bind to): the original file-scoped match -- a
#   waiver's `src` symbol/file equals the violation's `file` (either
#   the bare path or a `path::qualname` symref rooted at that path).
#   This is the CORRECT precision for those checks, not a shortcut:
#   one module-line violation per file has exactly one natural site.
#
# `violation.rule in _UNWAIVABLE_RULES` (currently just TEST008) short-
# circuits to `None` regardless of any matching `frob:waive` edge --
# by construction, not by omission; see `_UNWAIVABLE_RULES`'s comment.
#
# T-0276: a THIRD mode covers package/system-level violations (TEST003/
# TEST004, whose `violation.file` is an interface id like
# `crates/foo/src` or a system id, never a real single file) -- a
# waiver written in any file living under that package prefix also
# counts. Without this, such a violation's waiver could never match
# ANYTHING: no real source file's path is ever literally equal to a
# directory-shaped interface id, so the plain file-scoped comparison
# below always failed by construction (found while investigating why a
# `frob:waive TEST003 reason="..."` sitting in a rust integration test
# file reported `0 waived` in feldspar's adoption sweep -- traced to
# this, not to any check_type-based exclusion of `.rs` directives,
# which does not exist: `frob.graph.build_graph`/`_load_tests` are
# check_type-agnostic).
#
# T-0470: the package-prefix branch is gated to `_PACKAGE_SCOPED_RULES`
# ONLY -- it used to run for every symref-less violation regardless of
# rule, on the (empirically true today, but not future-proof) assumption
# that no other rule's `violation.file` is ever directory-shaped. TEST007
# also emits a directory-shaped `file` (a package id, `_test007_check_
# pair`), so it needed the same prefix reach TEST003/004 already had --
# but any FUTURE rule that reuses a bare directory/virtual id as `file`
# (a `[[system]]`-style id, a `design/...` construct id) would have
# silently inherited unbounded directory-prefix matching it was never
# reviewed for, purely because it happens to have no symref. Restricting
# the branch to an explicit allowlist means adding prefix reach to a new
# rule is a deliberate, reviewable one-line change, not a side effect of
# giving that rule a directory-shaped `file`.
# T-0289: a waiver may carry `ceiling="N"` (currently only meaningful for
# ARCH001) -- a reasoned "this long function is justified up to N lines"
# escape that re-fires once the function outgrows N, instead of muting the
# finding permanently. `_ceiling_ok` is generic (any rule whose Violation
# sets `metric` can use it), not ARCH001-specific, so a future rule with the
# same "reasoned up to a measured bound" shape does not need its own
# matching path.
# frob:ticket T-0470
# The only rules whose `Violation.file` is a directory/system id rather
# than a real leaf file with an extension -- see the T-0470 comment
# above `_match_waiver` for why this must be an explicit allowlist, not
# "every symref-less rule". Keep this in sync with any rule that starts
# emitting a package/system-shaped `file` (`_test003`, `_test004`,
# `_test007_check_pair` are the current three sites).
_PACKAGE_SCOPED_RULES = frozenset({"TEST003", "TEST004", "TEST007"})


def _ceiling_ok(waiver: Edge, violation: Violation) -> bool:
    """Whether `waiver` still covers `violation` given its optional
    `ceiling=` attribute: always true when no ceiling is set (or the
    violation carries no `metric` to compare); otherwise true only while
    `violation.metric <= ceiling`."""
    ceiling_text = waiver.attrs.get("ceiling")
    if ceiling_text is None or violation.metric is None:
        return True
    try:
        ceiling = int(ceiling_text)
    except ValueError:
        # Malformed ceiling value: fail open to "still waived" rather than
        # a crash -- WAIVE002-style validation of the attribute's shape is
        # a separate concern from matching, and a garbled ceiling is not
        # reason to un-suppress a violation the author clearly meant to
        # waive.
        return True
    return violation.metric <= ceiling


def _match_waiver(
    violation: Violation, waivers_by_rule: dict[str, list[Edge]]
) -> Edge | None:
    """The first WAIVE edge whose site matches `violation` (symbol-exact,
    file-scoped, or package-prefix -- see the comment above) AND whose
    optional `ceiling=` still covers it (`_ceiling_ok`), or None."""
    if violation.rule in _UNWAIVABLE_RULES:
        return None
    candidates = waivers_by_rule.get(violation.rule, ())
    if violation.symref is not None:
        for waiver in candidates:
            if waiver.src == violation.symref and _ceiling_ok(waiver, violation):
                return waiver
        return None
    package_scoped = violation.rule in _PACKAGE_SCOPED_RULES
    package_prefix = violation.file.rstrip("/") + "/"
    for waiver in candidates:
        waiver_file = waiver.src.split("::", 1)[0]
        if (
            waiver.src == violation.file
            or waiver_file == violation.file
            or (package_scoped and waiver_file.startswith(package_prefix))
        ) and _ceiling_ok(waiver, violation):
            return waiver
    return None


def _apply_waivers(
    violations: tuple[Violation, ...], snapshot: GraphSnapshot
) -> tuple[tuple[Violation, ...], tuple[Violation, ...]]:
    """Split `violations` into (kept, waived) using the snapshot's WAIVE edges."""
    waivers_by_rule = _waivers_by_rule(snapshot)
    kept: list[Violation] = []
    waived: list[Violation] = []
    for violation in violations:
        match = _match_waiver(violation, waivers_by_rule)
        if match is None:
            kept.append(violation)
            continue
        _log.debug(
            "waived: %s at %s:%d (%s)",
            violation.rule,
            violation.file,
            violation.line,
            match.attrs.get("reason", ""),
        )
        waived.append(
            violation.model_copy(
                update={
                    "waived": WaiverRef(
                        site=match.src, reason=match.attrs.get("reason", "")
                    )
                }
            )
        )
    return tuple(kept), tuple(waived)


# frob:doc docs/modules/gates.md#public-api
# frob:uses-contract src/frob/graph/__init__.py::build_graph
# frob:uses-contract src/frob/graph/lock.py::drift
# frob:uses-contract src/frob/tickets/__init__.py::load_queue
def _severity_overrides(root: Path | str) -> dict[str, Severity]:
    """The `[gates.severity]` table from frob.toml: rule id -> warn|error.

    This is how a legacy codebase adopts gates without a big-bang: noisy
    rules go to "warn" (visible, not blocking) and are flipped back to
    "error" as annotation coverage grows. Values other than warn/error are
    ignored with a warning -- never a crash on config typos.
    """
    toml_path = Path(root) / "frob.toml"
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("severity overrides: could not read %s: %s", toml_path, exc)
        return {}
    raw = data.get("gates", {}).get("severity", {})
    overrides: dict[str, Severity] = {}
    for rule, value in raw.items():
        if value in ("warn", "error"):
            overrides[rule] = Severity.WARN if value == "warn" else Severity.ERROR
        else:
            _log.warning(
                "severity overrides: %s=%r is not warn|error; ignored", rule, value
            )
    if overrides:
        _log.info("severity overrides active: %s", overrides)
    return overrides


def _apply_severity_overrides(
    violations: tuple[Violation, ...], root: Path | str
) -> tuple[Violation, ...]:
    """Re-severity `violations` per the `[gates.severity]` frob.toml table."""
    overrides = _severity_overrides(root)
    if not overrides:
        return violations
    return tuple(
        (
            v.model_copy(update={"severity": overrides[v.rule]})
            if v.rule in overrides
            else v
        )
        for v in violations
    )


_BRANCH_TICKET_RE = re.compile(r"^(T-\d{4})-")


# frob:doc docs/modules/gates.md#public-api
def active_ticket(root: Path, explicit: str | None) -> Option[str]:
    """`--ticket` wins; else the branch name matching `^(T-\\d{4})-`; else Nothing."""
    if explicit:
        _log.debug("active_ticket: explicit=%s", explicit)
        return Some(explicit)
    branch_result = current_branch(root)
    if branch_result.is_err:
        _log.debug("active_ticket: no branch context")
        return Nothing()
    match = _BRANCH_TICKET_RE.match(branch_result.danger_ok)
    if match is None:
        _log.debug(
            "active_ticket: branch %r has no ticket prefix", branch_result.danger_ok
        )
        return Nothing()
    _log.debug("active_ticket: branch-derived %s", match.group(1))
    return Some(match.group(1))


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------


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
# Coverage: COV001..COV004 and TODO001/TODO002
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#public-api
def coverage_gate(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    diff: Diff,
    tests: CollectedTests,
) -> tuple[Violation, ...]:
    """COV001..COV007, PLACE001, and TODO001/TODO002.

    `root` (repo root, T-0233) lets COV001 tell a *resolving* `frob:doc`
    edge apart from a broken one -- see `_resolved_documented_srcs`.
    """
    violations: list[Violation] = []
    violations.extend(_cov001(root, snapshot))
    violations.extend(_cov002(snapshot, queue, diff))
    violations.extend(_cov003(queue, tests))
    violations.extend(_cov004(queue))
    violations.extend(_cov005(root, snapshot, diff))
    violations.extend(_cov006(root, snapshot))
    violations.extend(_cov007(snapshot))
    violations.extend(_place001(root, snapshot))
    violations.extend(_todo001(snapshot, queue, diff))
    return tuple(violations)


def _documented_srcs(snapshot: GraphSnapshot) -> set[str]:
    """Symrefs carrying an explicit `frob:doc` edge (resolving or not)."""
    return {e.src for e in snapshot.edges if e.kind == EdgeKind.DOC}


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
            )
        )
    return tuple(violations)


def _open_scopes(queue: TicketQueue) -> list[tuple[str, tuple[str, ...]]]:
    """`(ticket_id, scope)` for every open ticket that declares a scope."""
    return [
        (t.id, t.scope)
        for t in queue.tickets.values()
        if t.state in _OPEN_STATES and t.scope
    ]


def _scope_covers(path: str, open_scopes: list[tuple[str, tuple[str, ...]]]) -> bool:
    """True if `path` matches any open ticket's scope (dir/ glob expansion
    and implicit ledger via `scope_matches`, T-0241)."""

    return any(scope_matches(path, scope) for _tid, scope in open_scopes)


def _ticket_edges(snapshot: GraphSnapshot, symref: str) -> list[Edge]:
    """The `frob:ticket` edges anchored on `symref`."""
    return [e for e in edges_from(snapshot, symref) if e.kind == EdgeKind.TICKET]


# frob:ticket T-0214
# frob:ticket T-0320
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_done_ticket_covers_own_closing_diff  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_done_ticket_without_grace_still_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageGate.test_cov002_marker_touch_without_state_transition_still_fires  # noqa: E501
def _bound_to_open_ticket(
    snapshot: GraphSnapshot, queue: TicketQueue, symref: str, diff: Diff | None = None
) -> bool:
    """True if `symref` has a `frob:ticket` edge to an open ticket, OR (T-0214
    grace window, T-0320 tightened) to a ticket whose OWN close is landing to
    `DONE` within this same uncommitted `diff`'s `tickets.md` hunk(s) AND
    whose state at the diff's base commit was actually open.

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
    ticket's state at `diff.base` (before this diff) to have been open --
    see `_ledger_states_at_base`. Once the close lands as its own commit
    (tickets.md drops out of the diff, the hunk no longer spans this
    ticket's marker, or the ticket was already `DONE` at `diff.base`), a
    `DONE` ticket's edge stops counting here, same as before, so a truly
    unrelated later touch to the symbol is still caught.
    """
    for edge in _ticket_edges(snapshot, symref):
        ticket = queue.tickets.get(edge.target)
        if ticket is None:
            continue
        if ticket.state in _OPEN_STATES:
            return True
        if (
            diff is not None
            and ticket.state == TicketState.DONE
            and _ticket_marker_in_diff_hunk(snapshot.root, diff, ticket.id)
            and _ledger_states_at_base(snapshot.root, diff.base).get(ticket.id)
            in _OPEN_STATES
        ):
            return True
    return False


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


def _ticket_marker_in_diff_hunk(root: str, diff: Diff, ticket_id: str) -> bool:
    """True if `tickets.md`'s `<!-- ticket:<ticket_id> -->` marker line falls
    inside one of `diff`'s `tickets.md` hunk spans.

    This is the T-0214-bypass fix: COV002 grace must be scoped to the
    specific ticket whose close is actually present in this diff's ledger
    hunk, not merely to "some" hunk existing in `tickets.md" -- otherwise a
    symbol bound to an unrelated, already-`DONE` ticket rides along on any
    other ticket's close and never gets flagged.
    """
    tickets_md_hunks = [h for h in diff.hunks if h.file == "tickets.md"]
    if not tickets_md_hunks:
        return False
    tickets_md_path = Path(root) / "tickets.md"
    if not tickets_md_path.is_file():
        return False
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = tickets_md_path.read_text(encoding="utf-8").splitlines()
    for hunk in tickets_md_hunks:
        start, end = hunk.span
        for lineno in range(max(1, start), end + 1):
            if lineno - 1 >= len(lines):
                break
            if marker in lines[lineno - 1]:
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
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff
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
    open_scopes = _open_scopes(queue)
    touched = sorted(_touched_symrefs(diff, snapshot))
    violations = [
        v
        for symref in touched
        for v in (_cov002_check_symref(snapshot, queue, symref, open_scopes, diff),)
        if v is not None
    ]
    return tuple(violations)


def _cov002_check_symref(
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    symref: str,
    open_scopes: list[tuple[str, tuple[str, ...]]],
    diff: Diff,
) -> Violation | None:
    """The COV002 `Violation` for one touched `symref`, or None when it is
    accounted for by a direct ticket edge (open, or `DONE` within this same
    uncommitted diff -- T-0214), its `.strata` module's edge, or an open
    ticket's scope."""
    if _bound_to_open_ticket(snapshot, queue, symref, diff):
        return None
    if _covered_by_strata_module(snapshot, queue, symref, diff):
        _log.debug("COV002: %s covered by its .strata module's ticket edge", symref)
        return None
    record = snapshot.symbols[symref]
    if _scope_covers(record.id.path, open_scopes):
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


def _cov004_one(
    ticket: Ticket,
    attachment,  # noqa: ANN001
    path: Path,
) -> tuple[Violation, ...]:
    """COV004 check for one attachment, resolved relative to the gate's root."""
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
    violations: list[Violation] = []
    for kind, target, was_public in old_bindings:
        if not was_public:
            continue
        for new_edge in new_by_key.get((kind, target), ()):
            record = snapshot.symbols.get(new_edge.src)
            if record is None or record.public:
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


def _old_directive_bindings(
    root: Path, base: str, file: str
) -> tuple[tuple[EdgeKind, str, bool], ...]:
    """`(kind, target, was_public)` for every `frob:` directive `file` carried
    at revision `base`, parsed from `git show <base>:<file>` -- empty (not an
    error) if the blob does not exist there (new file) or fails to parse.

    A throwaway same-suffix temp file is used so `frob.lang.parse_file`'s
    extension dispatch sees the right grammar; the temp path itself never
    leaks into the returned bindings (only `kind`/`target`/publicness do),
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
    bindings: list[tuple[EdgeKind, str, bool]] = []
    for edge in edges:
        qualname = edge.src.split("::", 1)[1] if "::" in edge.src else edge.src
        was_public = public_by_qualname.get(qualname, False)
        bindings.append((edge.kind, edge.target, was_public))
    return tuple(bindings)


# frob:ticket T-0506
def _cov006_public_wrapper_reachable(root: Path, edge: Edge) -> bool:
    """One-hop COV006 rescue: True if a PUBLIC symbol in the bound private
    target's own file both calls that target directly and is itself
    called, by name, from the test's own body -- the same-file
    test -> public-wrapper -> private-target shape `build_call_graph`
    cannot represent (it never records edges into public callees, T-0483).
    Scoped to this gate only; the shared `CallGraph` substrate is
    untouched so `frob.dup`/arch consumers keep their public-boundary-stop
    behavior.
    """
    from frob.graph.callgraph import _called_names, _short_name
    from frob.lang import parse_file

    target_file = edge.target.split("::", 1)[0]
    test_file = edge.src.split("::", 1)[0]
    target_qualname = edge.target.split("::", 1)[1]
    target_short = _short_name(target_qualname)

    target_parsed = parse_file(root / target_file)
    if target_parsed.is_err:
        return False
    target_symbols = target_parsed.danger_ok.symbols

    wrapper_short_names = {
        _short_name(sym.qualname)
        for sym in target_symbols
        if sym.public and target_short in _called_names(sym.body_tokens)
    }
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
    return bool(wrapper_short_names & _called_names(test_sym.body_tokens))


# frob:ticket T-0483
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
    """
    from frob.graph.callgraph import CallGraph, build_call_graph, closure

    graph_cache: dict[tuple[str, ...], CallGraph] = {}
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        target_record = snapshot.symbols.get(edge.target)
        if target_record is None or target_record.public:
            continue
        test_file = edge.src.split("::", 1)[0]
        target_file = edge.target.split("::", 1)[0]
        paths = (test_file,) if test_file == target_file else (test_file, target_file)
        graph = graph_cache.get(paths)
        if graph is None:
            graph = build_call_graph(root, paths)
            graph_cache[paths] = graph
        if edge.target in closure(graph, edge.src):
            continue
        if _cov006_public_wrapper_reachable(root, edge):
            continue
        _log.debug(
            "COV006: %s -> %s has no call-graph reachability", edge.src, edge.target
        )
        violations.append(
            Violation(
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
            )
        )
    return tuple(violations)


# frob:ticket T-0483
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


def _todo002_edges(snapshot: GraphSnapshot, queue: TicketQueue) -> list[Violation]:
    """TODO002: `frob:todo` edges bound to a non-open (or missing) ticket.

    Distinct failure mode from TODO001 (a bare, wholly untracked comment):
    here the work IS accounted for -- a `frob:todo` directive exists -- but
    the ticket it references is closed or missing, so the reference is
    dangling. Split from a single conflated TODO001 in T-0425 so the two
    modes can be tiered, waived, and reported independently, matching
    frob's own one-id-per-failure-mode convention (WAIVE001/002, COV001-004,
    TEST001-010, DUP001/002, PERF001-004).
    """
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TODO:
            continue
        target = queue.tickets.get(edge.target)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("TODO002: %s -> %s not open", edge.src, edge.target)
        violations.append(
            Violation(
                rule="TODO002",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"TODO002: frob:todo {edge.target} at {edge.src} is not bound to "
                    f"an open ticket; run: frob ticket new, then rebind"
                ),
            )
        )
    return violations


def _todo001_bare(snapshot: GraphSnapshot, diff: Diff) -> list[Violation]:
    """TODO001: bare todo/fixme comments in diff-touched, freshly parsed files.

    Distinct failure mode from TODO002 (a dangling `frob:todo` reference):
    here the work is not accounted for at all -- no ticket, no directive --
    so the fix is "file a ticket and convert to `frob:todo T-####`" rather
    than "fix the dangling reference". See `_todo002_edges`.
    """
    from frob.lang import parse_file  # local import: keep gates' top import list lean

    root = Path(snapshot.root)
    touched = sorted(_touched_files(diff))
    violations: list[Violation] = []
    for file in touched:
        parsed = parse_file(root / file)
        if parsed.is_err:
            continue
        for comment in parsed.danger_ok.comments:
            violations.extend(_todo001_bare_comment(file, comment))
    return violations


def _todo001_bare_comment(file: str, comment) -> list[Violation]:  # noqa: ANN001
    """Every bare (not `frob:`-prefixed) todo/fixme line inside one comment,
    as TODO001 `Violation`s."""
    violations: list[Violation] = []
    for offset, line_text in enumerate(comment.text.splitlines() or [comment.text]):
        if line_text.strip().startswith("frob:"):
            continue
        if _TODO_RE.search(line_text) is None:
            continue
        lineno = comment.span[0] + offset
        _log.debug("TODO001: bare TODO/FIXME at %s:%d", file, lineno)
        violations.append(
            Violation(
                rule="TODO001",
                severity=Severity.WARN,
                file=file,
                line=lineno,
                message=(
                    f"TODO001: bare TODO/FIXME at {file}:{lineno}; bind it: "
                    f"frob:todo <ticket-id>"
                ),
            )
        )
    return violations


def _todo001(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff
) -> tuple[Violation, ...]:
    """TODO001 + TODO002: a bare todo/fixme comment in a diff-touched file
    (parsed fresh via `frob.lang`, cheap since scoped to the diff, not the
    whole tree), and a `frob:todo` bound to a non-open ticket -- two distinct
    failure modes, each raised under its own rule id (see `_todo001_bare`
    and `_todo002_edges`)."""
    return (
        *_todo002_edges(snapshot, queue),
        *_todo001_bare(snapshot, diff),
    )


# ---------------------------------------------------------------------------
# Scope digest, scope, and pre-work gates
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#public-api
def scope_digest(scope: Sequence[str], snapshot: GraphSnapshot) -> str:
    """Sha256 over the sorted `(file, hash)` pairs of files matching `scope`.

    THE one implementation: `frob ticket start/sweep` records it and
    `prework_gate` compares against it -- a second copy of this hash is how
    PRE001 becomes permanently stale (it happened; see tests/test_prework_parity.py).
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


def _commit_exempts_file(
    root: Path, sha: str, file: str, ticket: Ticket, queue: TicketQueue
) -> bool:
    """True if commit `sha`'s subject names another ticket (not `ticket`) whose
    own declared `scope` covers `file` -- the SCOPE001 cross-ticket exemption
    (T-0108): a commit's authorship is attributed by the ticket id its subject
    references, not by whichever ticket happens to be running the check now."""

    subject = _commit_subject(root, sha)
    if subject.is_nothing:
        return False
    for ref in _TICKET_REF_RE.findall(subject.danger_some):
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
    branch (T-0108)."""

    if not ticket.scope:
        _log.debug(
            "scope_gate: %s has no declared scope, nothing to enforce", ticket.id
        )
        return ()
    touched = sorted(_touched_files(diff))
    violations = [
        v
        for file in touched
        for v in (_scope_gate_check_file(file, ticket, diff, root, queue),)
        if v is not None
    ]
    return tuple(violations)


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
    return ()


# ---------------------------------------------------------------------------
# Invariant gate
# ---------------------------------------------------------------------------


def _invariant_anchors(snapshot: GraphSnapshot) -> set[str]:
    """Invariant ids carrying a `frob:invariant` anchor edge in code."""
    return {e.target for e in snapshot.edges if e.kind == EdgeKind.INVARIANT}


# frob:waive DUP001 reason="Violation-builder boilerplate shared shape \
# with _inv002 below; distinct rule ids and distinct remediation messages \
# (missing evidence vs missing anchor) -- structural coincidence"
def _inv001(inv: Invariant) -> Violation:
    """INV001: an invariant with no standing evidence."""
    return Violation(
        rule="INV001",
        severity=Severity.ERROR,
        file=inv.path,
        line=0,
        message=(
            f"INV001: {inv.id} has no evidence resolving to a collected "
            f"test or loaded policy rule; add a passing test or POL rule "
            f"to its evidence list"
        ),
    )


# frob:waive DUP001 reason="Violation-builder boilerplate shared shape \
# with _inv001 above; distinct rule id and message -- structural \
# coincidence"
def _inv002(inv: Invariant) -> Violation:
    """INV002: an invariant with no code anchor."""
    return Violation(
        rule="INV002",
        severity=Severity.ERROR,
        file=inv.path,
        line=0,
        message=(
            f"INV002: {inv.id} has no frob:invariant anchor in code; "
            f"add: frob:invariant {inv.id} at the enforcing site"
        ),
    )


# frob:doc docs/modules/gates.md#public-api
def invariant_gate(
    invariants: tuple[Invariant, ...],
    snapshot: GraphSnapshot,
    tests: CollectedTests,
    policy_rule_ids: frozenset[str] = frozenset(),
) -> tuple[Violation, ...]:
    """INV001 (no evidence) and INV002 (no code anchor).

    **Deviation**: adds an optional `policy_rule_ids` parameter beyond
    docs/modules/gates.md's `(invariants, snapshot, tests)` signature so INV001 can
    treat a loaded policy rule id as valid evidence, per the doc's own
    evidence-list example (`POL-no-direct-lock-write`); without it there
    would be no way for this pure function to see policy state at all.
    """
    anchors = _invariant_anchors(snapshot)
    violations: list[Violation] = []
    for inv in invariants:
        has_evidence = any(
            _evidence_collected(item, tests) or item in policy_rule_ids
            for item in inv.evidence
        )
        if not inv.evidence or not has_evidence:
            _log.debug("INV001: %s has no standing evidence", inv.id)
            violations.append(_inv001(inv))
        if inv.id not in anchors:
            _log.debug("INV002: %s has no code anchor", inv.id)
            violations.append(_inv002(inv))
    return tuple(violations)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0462
_DOC_INVARIANT_MARKER_RE = re.compile(r"<!--\s*frob:invariant\s+(INV-\d{3})\s*-->")

# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
# Markdown-side waiver marker: `<!-- frob:waive INV003 reason="..." -->`.
# `_match_waiver` (the code-side waiver path) keys off graph edges, which
# doc prose carries none of -- this is a separate, file/section-scoped
# marker so a genuine-but-unprovable claim (prose describing a design
# intent rather than an enforced behavior) can be dispositioned honestly
# instead of either being hand-bound to a fake invariant or silently
# ignored. A missing/empty reason does not count as a waiver (same
# honesty requirement as `frob:waive`'s code-side WAIVE001).
_DOC_WAIVE_MARKER_RE = re.compile(
    r'<!--\s*frob:waive\s+(INV00[34])\s+reason="([^"]+)"\s*-->'
)

# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
# INV003 is scoped to these repo-relative directories (spec-normative
# design/module docs), not all of docs/**.md -- exclusivity claims worth
# gating live in the docs that describe enforced contracts; a narrative
# design doc or changelog making a passing "only" remark is not the same
# failure mode T-0462 named. INV004 (the coarser advisory signal) keeps
# scanning all of docs/ -- see `inv004_gate`.
INV003_SPEC_DIRS: tuple[str, ...] = ("docs/modules", "docs/strata")


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
def _file_has_reasoned_doc_waiver(path: Path, rule: str) -> bool:
    """True if `path` carries a `<!-- frob:waive <rule> reason="..." -->`
    marker anywhere in the file, with a non-empty reason.

    Deliberately NOT folded into `_inv003_doc_violations`'s own body: that
    function's `frob:ticket T-0462` directive is one of several bindings
    sharing that same ticket-id target across this file (T-0462 also
    covers `inv003_gate`, still public) -- COV005's rebind check matches
    old/new directive bindings by `(kind, target)` alone, so editing
    inside an already-ticket-tagged private helper whose target is shared
    with a public sibling elsewhere in the file spuriously reads as "this
    directive rode onto a new private symbol" even though nothing rebound.
    Applying the waiver filter from the (public, freshly-tagged) gate
    function instead avoids that false positive entirely.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("%s: could not read %s for waiver check: %s", rule, path, exc)
        return False
    return any(
        matched_rule == rule and reason
        for matched_rule, reason in _DOC_WAIVE_MARKER_RE.findall(text)
    )


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
def _inv004_waived_headings(text: str) -> frozenset[str]:
    """Heading text of every section in `text` that carries a reasoned
    `<!-- frob:waive INV004 reason="..." -->` marker (see
    `_file_has_reasoned_doc_waiver`'s docstring for why this filters at
    the gate-function level rather than inside `_inv004_doc_violations`).
    """
    waived: set[str] = set()
    for section in _markdown_sections(text):
        if not any(
            rule == "INV004" and reason
            for rule, reason in _DOC_WAIVE_MARKER_RE.findall(section)
        ):
            continue
        heading_match = re.match(r"^(#{1,6}\s.*)$", section, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else "(no heading)"
        waived.add(heading)
    return frozenset(waived)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
_INV004_MESSAGE_HEADING_RE = re.compile(r"section (.+?) describes behavior")


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
def _inv004_message_heading(message: str) -> str | None:
    """Recover the exact heading string `_inv004_doc_violations` embedded
    (via `heading!r`) in one INV004 `Violation.message`, or `None` if the
    message does not match the expected shape. `ast.literal_eval` undoes
    the `repr()` reliably regardless of whether Python chose single- or
    double-quote style for a heading containing an apostrophe."""
    match = _INV004_MESSAGE_HEADING_RE.search(message)
    if match is None:
        return None
    try:
        value = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0462
def _inv003_doc_violations(
    root: Path, path: Path, known_ids: frozenset[str]
) -> tuple[Violation, ...]:
    """INV003 findings for one doc file: an exclusivity claim
    (`frob.gates.invariants.find_exclusivity_claims`) with no
    `<!-- frob:invariant INV-### -->` marker in the same file naming a
    REAL (loaded) invariant id.

    File-granularity, not per-section: a doc large enough to need
    section-level binding should already be split, and file granularity
    is enough to catch the actual failure mode this ticket names --
    prose asserting exclusivity with nothing tracking whether it still
    holds.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("INV003: could not read %s: %s", path, exc)
        return ()
    claims = find_exclusivity_claims(text)
    if not claims:
        return ()
    bound_ids = set(_DOC_INVARIANT_MARKER_RE.findall(text))
    if bound_ids & known_ids:
        return ()
    rel = path.relative_to(root).as_posix()
    return (
        Violation(
            rule="INV003",
            severity=Severity.WARN,
            file=rel,
            line=0,
            message=(
                f"INV003: {rel} makes an exclusivity/normative claim "
                f"({', '.join(sorted(claims))}) with no "
                f"`<!-- frob:invariant INV-### -->` marker in the file "
                f"naming a real invariant -- bind an invariant that "
                f"covers the claim, or reword to drop the exclusivity "
                f"language if it isn't actually enforced"
            ),
        ),
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0462
def inv003_gate(root: Path, invariants: tuple[Invariant, ...]) -> tuple[Violation, ...]:
    """INV003: every exclusivity claim in a spec-normative doc
    (`INV003_SPEC_DIRS`) needs a bound invariant.

    T-0509: scoped to `INV003_SPEC_DIRS` (docs/modules, docs/strata), not
    all of docs/**.md -- exclusivity claims worth gating describe enforced
    contracts, which is what those two trees are for; a narrative design
    doc or changelog making a passing "only" remark is a different failure
    mode than T-0462 named. Combined with the stronger claim-shape scan
    (`find_exclusivity_claims`: noise-stripped, verb-bearing sentences
    only) and markdown-side `frob:waive` support (`_DOC_WAIVE_MARKER_RE`),
    this narrows the original ~765-warning INV003+INV004 pool to a
    genuinely reviewable set (T-0509's Done report has the exact counts).

    WARN severity (does not fail `frob check`), not ERROR like INV001/
    INV002: even after calibration, a claim can still be genuine design
    intent rather than an enforced behavior -- WARN surfaces the signal
    for human triage rather than forcing a bind-or-waive on every hit.
    """
    known_ids = frozenset(inv.id for inv in invariants)
    violations: list[Violation] = []
    for spec_dir in INV003_SPEC_DIRS:
        docs_dir = root / spec_dir
        if not docs_dir.is_dir():
            continue
        for path in iter_files(docs_dir, suffix=".md"):
            file_violations = _inv003_doc_violations(root, path, known_ids)
            if file_violations and _file_has_reasoned_doc_waiver(path, "INV003"):
                _log.debug("INV003: %s waived by markdown frob:waive marker", path)
                continue
            violations.extend(file_violations)
    return tuple(violations)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
_MD_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
def _markdown_sections(text: str) -> tuple[str, ...]:
    """Split `text` into ATX-heading-delimited sections (each section runs
    from one `#`-line up to, but not including, the next); a file with no
    heading at all is one whole-file section.

    Coarser than a full outline (T-0452's density signal doesn't need
    heading level/nesting, just "a chunk of prose"), so this is a plain
    split on heading boundaries rather than a hierarchical tree.
    """
    starts = [m.start() for m in _MD_HEADING_RE.finditer(text)]
    if not starts:
        return (text,) if text.strip() else ()
    bounds = [*starts, len(text)]
    return tuple(text[bounds[i] : bounds[i + 1]] for i in range(len(starts)))


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
def _inv004_doc_violations(root: Path, path: Path) -> tuple[Violation, ...]:
    """INV004 findings for one doc file: a section using normative
    language (`frob.gates.invariants.find_normative_claims`) that anchors
    ZERO `<!-- frob:invariant INV-### -->` markers at all -- the inverse
    of INV003's per-claim check, a coarser "this region looks
    under-specified" signal.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("INV004: could not read %s: %s", path, exc)
        return ()
    rel = path.relative_to(root).as_posix()
    violations: list[Violation] = []
    for section in _markdown_sections(text):
        claims = find_normative_claims(section)
        if not claims:
            continue
        if _DOC_INVARIANT_MARKER_RE.search(section) is not None:
            continue
        heading_match = re.match(r"^(#{1,6}\s.*)$", section, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else "(no heading)"
        violations.append(
            Violation(
                rule="INV004",
                severity=Severity.WARN,
                file=rel,
                line=0,
                message=(
                    f"INV004: {rel} section {heading!r} describes behavior "
                    f"({', '.join(sorted(claims))}) but anchors zero "
                    f"invariants -- likely under-specified; add an "
                    f"`invariants/INV-###.md` plus a "
                    f"`<!-- frob:invariant INV-### -->` marker in this "
                    f"section if the behavior is meant to be guaranteed"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0452
def inv004_gate(root: Path) -> tuple[Violation, ...]:
    """INV004 (advisory): a docs/**.md section that describes behavior
    (normative language) but anchors zero invariants at all.

    Always WARN -- section-level under-specification is a suggestion to
    formalize, not a broken obligation; never fails `frob check`.
    """
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return ()
    violations: list[Violation] = []
    for path in iter_files(docs_dir, suffix=".md"):
        file_violations = _inv004_doc_violations(root, path)
        if not file_violations:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("INV004: could not re-read %s for waivers: %s", path, exc)
            violations.extend(file_violations)
            continue
        waived_headings = _inv004_waived_headings(text)
        if not waived_headings:
            violations.extend(file_violations)
            continue
        for v in file_violations:
            heading = _inv004_message_heading(v.message)
            if heading is not None and heading in waived_headings:
                _log.debug(
                    "INV004: %s section %r waived by markdown marker", path, heading
                )
                continue
            violations.append(v)
    return tuple(violations)


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
        _case_count(valid, tests)
        if edges
        else _inferred_unit_cases(record.symref, tests)
    )
    if effective == 0 and not edges:
        return _test001_no_unit_test(record)
    if effective < cfg.min_unit_cases:
        return _test002_below_min(record, effective, cfg)
    return None


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
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
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
        verdict = _test001_002_one(record, unit_edges, tests, cfg, snapshot)
        if verdict is not None:
            violations.append(verdict)
    return tuple(violations)


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
    count = _case_count(valid, tests)
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
        count = _case_count(valid, tests)
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


def _test005_symbols(
    snapshot: GraphSnapshot, data: CoverageData, cfg: TestPolicy
) -> list[Violation]:
    """TEST005 per-symbol branch-coverage floor.

    Skips test-file symbols exactly like TEST001/TEST002 do (T-0301): a
    test-file helper/fixture is not a public interface TEST005's floor is
    meant to police, and measuring it forced env-gated test fixtures into
    noise waivers just to stay green (lithos FROBLEMS 2026-07-19)."""
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or is_test_file(record.id.path)
        ):
            continue
        pct = data.symbol_branch.get(record.symref)
        if pct is not None and pct < cfg.unit_branch_cov:
            violations.append(_test005_symbol_violation(record, pct, cfg))
    return violations


def _test005_symbol_violation(record, pct: float, cfg: TestPolicy) -> Violation:  # noqa: ANN001
    """A single TEST005 per-symbol branch-coverage-floor violation."""
    _log.debug(
        "TEST005: %s branch cov %.1f%% < %d%%",
        record.symref,
        pct,
        cfg.unit_branch_cov,
    )
    return Violation(
        rule="TEST005",
        severity=Severity.WARN,
        file=record.id.path,
        line=record.span[0],
        message=(
            f"TEST005: {record.symref} branch coverage {pct:.1f}% below "
            f"unit_branch_cov={cfg.unit_branch_cov}%; add tests, then: "
            f"make coverage"
        ),
        symref=record.symref,
    )


def _test005_modules(data: CoverageData, cfg: TestPolicy) -> list[Violation]:
    """TEST005 per-module line-coverage floor."""
    violations: list[Violation] = []
    for module, pct in data.module_line.items():
        if pct < cfg.module_line_cov:
            _log.debug(
                "TEST005: %s line cov %.1f%% < %d%%", module, pct, cfg.module_line_cov
            )
            violations.append(
                Violation(
                    rule="TEST005",
                    severity=Severity.WARN,
                    file=module,
                    line=0,
                    message=(
                        f"TEST005: {module} line coverage {pct:.1f}% below "
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
            violations.append(_test005_system_violation(system, avg, cfg))
    return violations


def _test005_system_violation(
    system: SystemSpec, avg: float, cfg: TestPolicy
) -> Violation:
    """A single TEST005 per-system aggregate line-coverage-floor violation."""
    _log.debug(
        "TEST005: system %s line cov %.1f%% < %d%%",
        system.id,
        avg,
        cfg.system_line_cov,
    )
    return Violation(
        rule="TEST005",
        severity=Severity.WARN,
        file=f"[[system]] {system.id}",
        line=0,
        message=(
            f"TEST005: system {system.id} line coverage {avg:.1f}% below "
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
        *_test005_symbols(snapshot, data, cfg),
        *_test005_modules(data, cfg),
        *_test005_systems(systems, data, cfg),
    )


# frob:ticket T-0464
_TEST011_JOIN_FLOOR = 0.5


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


def _exclude_filtered_coverage(
    data: CoverageData, snapshot: GraphSnapshot
) -> CoverageData:
    """Re-filter `data` against `[graph] exclude`.

    `coverage.xml` is produced straight from whatever `pytest --cov`
    walked, so it does not honor `[graph] exclude` (T-0148) the way
    `frob.graph`'s own walk does -- e.g. `src/frob/scaffold/data/**`
    (jinja templates rendered into OTHER repos, never imported/executed
    here) shows up as near-random "line coverage" of template source
    text. Re-filtering `data.module_line`/`.symbol_branch` here, against
    the same excludes every other file-walking surface already respects
    (`frob.excludes`), keeps TEST005 measuring only this package's own
    maintained modules.
    """
    exclude_globs = load_exclude_globs(Path(snapshot.root))
    if not exclude_globs:
        return data
    return CoverageData(
        source_sha=data.source_sha,
        symbol_branch={
            symref: pct
            for symref, pct in data.symbol_branch.items()
            if not is_excluded(symref.split("::", 1)[0], exclude_globs)
        },
        module_line={
            path: pct
            for path, pct in data.module_line.items()
            if not is_excluded(path, exclude_globs)
        },
        root_join_ok=data.root_join_ok,
        attempted_roots=data.attempted_roots,
        stale_by_mtime=data.stale_by_mtime,
        module_join_fraction=data.module_join_fraction,
    )


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


def _test006_stale(
    stamped_hashes: dict, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """The TEST006 violation if any stamped file hash moved, else empty."""
    for path, current_hash in snapshot.file_hashes.items():
        stamped = stamped_hashes.get(path)
        if stamped is not None and stamped != current_hash:
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


# frob:doc docs/modules/gates.md#public-api
def test_gate(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    tests: CollectedTests,
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST001..TEST011. Interfaces derived from packages with public symbols
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
    problem rather than a real regression (see `_test011_freshness`)."""
    violations: list[Violation] = []
    violations.extend(_test001_002(snapshot, tests, cfg))
    violations.extend(_test003(snapshot, tests, cfg))
    violations.extend(_test007_pairs(snapshot, tests, cfg))
    violations.extend(_test004(systems, snapshot, tests))
    violations.extend(_test005(snapshot, systems, coverage, cfg))
    violations.extend(_test006(snapshot))
    violations.extend(_test009(snapshot, tests, cfg))
    violations.extend(_test010_violations(snapshot))
    return tuple(violations)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_systems(doc: dict) -> tuple[SystemSpec, ...]:
    """Parse the `[[system]]` array from a frob.toml document; bad entries skipped."""
    systems: list[SystemSpec] = []
    for entry in doc.get("system", []):
        try:
            systems.append(
                SystemSpec(
                    id=entry["id"],
                    entrypoint=entry.get("entrypoint", ""),
                    min_e2e=entry.get("min_e2e", 1),
                    paths=tuple(entry.get("paths", ())),
                )
            )
        except (KeyError, ValidationError) as exc:
            _log.warning("_load_test_config: bad [[system]] entry: %s", exc)
    return tuple(systems)


def _load_test_config(root: Path) -> tuple[TestPolicy, tuple[SystemSpec, ...]]:
    """`[testing]` -> `TestPolicy`, `[[system]]` -> `SystemSpec` tuple;
    both optional."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return TestPolicy(), ()
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, ValueError) as exc:
        _log.warning("_load_test_config: could not parse %s: %s", toml_path, exc)
        return TestPolicy(), ()

    testing_tbl = doc.get("testing", {})
    fields = TestPolicy.model_fields
    try:
        policy = TestPolicy(**{k: v for k, v in testing_tbl.items() if k in fields})
    except ValidationError as exc:
        _log.warning("_load_test_config: bad [testing] table: %s", exc)
        policy = TestPolicy()

    return policy, _load_systems(doc)


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0004
# frob:waive TEST005 reason="decisions_gate 88.9% branch cover, debt T-0160"
def decisions_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEC001/DEC002: decision records and their code anchors (T-0004).

    Runs only when a `decisions/` directory exists (opt-in by convention).
    A malformed record fails loudly rather than silently degrading, since
    the record set is a contract surface like the ticket queue.
    """
    from frob.gates.decisions import decision_gate, decisions_dir, load_decisions

    root = Path(root)
    if not decisions_dir(root).exists():
        return ()
    loaded = load_decisions(root)
    if loaded.is_err:
        return (
            Violation(
                rule="DEC000",
                severity=Severity.ERROR,
                file="decisions/",
                line=0,
                message=f"DEC000: decision records unreadable: {loaded.danger_err}",
            ),
        )
    return decision_gate(loaded.danger_ok, snapshot)


# ---------------------------------------------------------------------------
# TICK001 / TICK002: ticket-id collision invariant (T-0162, decision record
# in docs/modules/tickets.md#decision-record-t-0162)
# ---------------------------------------------------------------------------


# frob:ticket T-0162
def _tick001_duplicate_ids(root: Path) -> tuple[Violation, ...]:
    """TICK001: an id present in BOTH the active and archive ledgers.

    Defense in depth, not the primary mechanism: `_load_merged` (frob.tickets)
    already hard-Errs `run_gates` itself (GateError.QueueUnavailable) the
    moment ledger loading sees this, which is louder than any Violation --
    the whole `frob check` run refuses to produce a report at all. This rule
    exists so that stays true even if a future change makes ledger loading
    more permissive; see the decision record for why duplicate-id detection
    is split this way instead of only living in one place.
    """
    active = _tickets_load_all(root)
    archived = _tickets_load_archive(root)
    if active.is_err or archived.is_err:
        return ()
    overlap = sorted(set(active.danger_ok) & set(archived.danger_ok))
    return tuple(
        Violation(
            rule="TICK001",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=(
                f"TICK001: {tid} exists in both tickets.md and "
                f"tickets-archive.md -- resolve the collision (frob ticket "
                f"renumber one of them) before the ledger can be trusted"
            ),
        )
        for tid in overlap
    )


# frob:ticket T-0162
def _tick002_draft_on_default(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK002: a T-draft-* provisional id still present while `root` is on
    the default branch -- the finalize step (T-0162's provisional-id
    mechanism; `frob ticket land`/T-0176 will call `finalize_draft`
    automatically) was skipped, failed, or never run. A draft id reaching
    the default branch means the collision-proofing this whole mechanism
    exists for silently did not happen, so this rule is unwaivable
    (`_UNWAIVABLE_RULES`) for the same reason TEST008 is.
    """
    if not on_default_branch(root):
        return ()
    return tuple(
        Violation(
            rule="TICK002",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=(
                f"TICK002: draft id {tid} survived onto the default branch -- "
                f"finalize it: `frob ticket renumber {tid} T-####` (or the "
                f"land step, once T-0176 lands)"
            ),
        )
        for tid in sorted(queue.tickets)
        if is_draft_id(tid)
    )


# frob:ticket T-0409
_TICK003_DEFAULT_WARN = 20
_TICK003_DEFAULT_ERROR = 60


def _tick003_thresholds(root: Path) -> tuple[int, int]:
    """`(warn_at, error_at)` un-archived-closed-ticket count thresholds
    (T-0409) from `frob.toml`'s `[tickets]` table (`stale_archive_warn`/
    `stale_archive_error`), defaulting to
    `(_TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR)`. A missing/malformed
    `frob.toml` degrades to the defaults rather than blocking the gate --
    ledger hygiene is a hint, not something a config-loading hiccup should
    take down."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR
    try:
        with toml_path.open("rb") as fh:
            table = tomllib.load(fh).get("tickets", {})
        return (
            int(table.get("stale_archive_warn", _TICK003_DEFAULT_WARN)),
            int(table.get("stale_archive_error", _TICK003_DEFAULT_ERROR)),
        )
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tick003: frob.toml unreadable/malformed (%s), using defaults", exc
        )
        return _TICK003_DEFAULT_WARN, _TICK003_DEFAULT_ERROR


def _tick003_violation(count: int, severity: Severity, threshold: int) -> Violation:
    """One TICK003 `Violation` at `severity`, naming `count` and the
    `threshold` it crossed, always pointing at `frob ticket archive` as the
    fix (T-0409)."""
    return Violation(
        rule="TICK003",
        severity=severity,
        file="tickets.md",
        line=0,
        message=(
            f"TICK003: {count} closed ticket(s) sitting un-archived in "
            f"tickets.md (threshold {threshold}) -- run `frob ticket "
            f"archive` (in a quiet window, no in-flight worktrees) to clear it"
        ),
    )


def _tick003_stale_archive(root: Path) -> tuple[Violation, ...]:
    """TICK003 (T-0409): WARN (escalating to ERROR past a hard cap) when
    the ACTIVE ledger (never the archive -- an already-archived closed
    ticket is not a hygiene problem) holds more than a configurable
    threshold of closed (done/dropped) tickets un-archived.

    Resurrection-safe by construction: this gate only ever COUNTS and
    recommends `frob ticket archive`; it never archives anything itself, so
    it can never interact with the land/splice path's archive-resurrection
    guards (`_drop_resurrected_ids`, `splice_ledger`, docs/modules/
    tickets.md#frob-ticket-land) -- those guard a WRITE this gate never
    performs. `frob ticket archive` itself should still only be run in a
    quiet window (no active worktrees), per the same known hazard; this
    gate's message says so but cannot enforce it.
    """
    active = _tickets_load_all(root)
    if active.is_err:
        return ()
    count = len(closed_ticket_ids(TicketQueue(tickets=active.danger_ok)))
    warn_at, error_at = _tick003_thresholds(root)
    if count > error_at:
        return (_tick003_violation(count, Severity.ERROR, error_at),)
    if count > warn_at:
        return (_tick003_violation(count, Severity.WARN, warn_at),)
    return ()


# frob:ticket T-0411
_TICK004_DEFAULT_ROT_DAYS = {
    Priority.CRITICAL: 3,
    Priority.HIGH: 7,
    Priority.MEDIUM: 30,
    Priority.LOW: 90,
}


# frob:ticket T-0411
def _tick004_rot_thresholds(root: Path) -> dict[Priority, int]:
    """Per-priority rot-day thresholds (T-0411) from `frob.toml`'s
    `[tickets]` table (`rot_days_critical`/`rot_days_high`/
    `rot_days_medium`/`rot_days_low`), defaulting to
    `_TICK004_DEFAULT_ROT_DAYS`. Same fail-open-to-defaults shape as
    `_tick003_thresholds` -- a missing/malformed `frob.toml` degrades to
    the defaults rather than blocking the gate."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return dict(_TICK004_DEFAULT_ROT_DAYS)
    try:
        with toml_path.open("rb") as fh:
            table = tomllib.load(fh).get("tickets", {})
        return {
            priority: int(table.get(f"rot_days_{priority.value}", default))
            for priority, default in _TICK004_DEFAULT_ROT_DAYS.items()
        }
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tick004: frob.toml unreadable/malformed (%s), using defaults", exc
        )
        return dict(_TICK004_DEFAULT_ROT_DAYS)


# frob:ticket T-0411
def _tick004_queue_rot(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK004 (T-0411): WARN (escalating to ERROR at 2x threshold) per
    queued/planned ticket whose priority-specific rot-day threshold has
    been crossed since `created` -- the queue-health signal T-0411's
    Description asks for: "we forgot we have a stack of things and only
    end up popping off the top half" becomes a visible gate finding
    instead of a silent, age-only queue. Only QUEUED/PLANNED tickets are
    considered (an in-progress/blocked ticket is not rotting, it is being
    worked or is explicitly waiting on a blocker)."""
    thresholds = _tick004_rot_thresholds(root)
    today = date.today()
    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state not in (TicketState.QUEUED, TicketState.PLANNED):
            continue
        age_days = (today - t.created).days
        threshold = thresholds[t.priority]
        if age_days <= threshold:
            continue
        severity = Severity.ERROR if age_days > threshold * 2 else Severity.WARN
        violations.append(
            Violation(
                rule="TICK004",
                severity=severity,
                file="tickets.md",
                line=0,
                message=(
                    f"TICK004: {t.id} ({t.priority.value} priority) has sat "
                    f"{t.state.value} for {age_days}d (threshold {threshold}d) "
                    f"-- it is rotting; work it, re-prioritize it "
                    f"(`frob ticket priority {t.id} <level>`), or drop it"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/modules/tickets.md#decision-record-t-0162
def tickets_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK001/TICK002/TICK003/TICK004: the T-0162 ticket-id collision
    invariant gate, plus the T-0409 ledger-hygiene check and the T-0411
    priority-rot check."""
    return (
        _tick001_duplicate_ids(root)
        + _tick002_draft_on_default(root, queue)
        + _tick003_stale_archive(root)
        + _tick004_queue_rot(root, queue)
    )


# ---------------------------------------------------------------------------
# SYS001 / SYS002: strata directive <-> design binding (T-0080)
# ---------------------------------------------------------------------------

_SYS_DIRECTIVE_KINDS: dict[EdgeKind, str] = {
    EdgeKind.CHANNEL: "channels",
    EdgeKind.BOUNDARY: "boundaries",
    EdgeKind.SECRET: "secrets",
}
#: Mirrors `frob.strata._design_load.DEFAULT_DESIGN_DIR`. Duplicated as a
#: bare literal (rather than imported) so `_design_dir` -- called as
#: `sys_gate`'s FIRST statement, before the opt-in existence check below --
#: never touches `frob.strata` for a repo that has no design dir at all
#: (T-0135: `frob.strata` transitively imports `_facts.py`, which needs the
#: `strata_core` native extension, and a standalone tool install must not
#: pay that cost, or risk that import failing, on every single repo).
_DEFAULT_DESIGN_DIR = "design"


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `_DEFAULT_DESIGN_DIR`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            return (
                tomllib.load(fh)
                .get("strata", {})
                .get("design_dir", _DEFAULT_DESIGN_DIR)
            )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("sys_gate: frob.toml unreadable: %s", exc)
        return _DEFAULT_DESIGN_DIR


def _sys004_native_hint(root: Path) -> str:
    """Extra SYS004 clause naming `make core` as the likely remedy when a
    declared native is stale against its own source tree (T-0248's
    `frob.strata.stale_natives`), distinguishing a grammar/native version
    mismatch from a genuine syntax error in the `.strata` file itself --
    the original T-0166 incident's fix (2): a design file failed to load
    with a mysterious "unknown construct" error because the built
    `strata_core` predated a landed grammar change, and nothing at the
    SYS004 call site said so. Returns the empty string when no native is
    stale, so callers can unconditionally append it to the base message."""
    from frob.strata import stale_natives

    stale = stale_natives(root)
    if not stale:
        return ""
    names = ", ".join(sorted({s.spec.name for s in stale}))
    return (
        f" -- built extension(s) [{names}] are older than their own source "
        f"tree, which can itself cause a parse failure on a construct the "
        f"grammar added since the last build; run `make core` first and "
        f"re-check before treating this as a genuine `.strata` syntax error"
    )


# frob:tests tests/test_gates.py::TestSysGate.test_sys004_load_failure
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_suppresses_sys001
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_names_stale_native_as_likely_remedy  # noqa: E501
def _sys004(design_ids, root: Path) -> list[Violation]:
    """SYS004: a `.strata` design file itself failed to parse/elaborate.

    Reported as its own rule, distinct from SYS001, because a load failure
    and a dangling reference are different problems with different fixes
    (fix the design file vs. fix the directive) -- collapsing them would
    misdirect whoever reads the message (reviewer-caught, T-0080 REJECT
    round 1). Also names a stale native build as a likely cause (T-0248
    follow-up) when one is detected, per the T-0166 incident precedent."""
    native_hint = _sys004_native_hint(root)
    return [
        Violation(
            rule="SYS004",
            severity=Severity.ERROR,
            file=error.path,
            line=0,
            message=(
                f"SYS004: {error.path} failed to load ({error.error.value}); "
                f"fix the .strata file -- SYS001 dangling-reference checks are "
                f"suppressed while any design file fails to load, since ids are "
                f"merged across all design files and a missing sibling's ids "
                f"cannot be told apart from a genuinely dangling reference"
                f"{native_hint}"
            ),
        )
        for error in design_ids.errors
    ]


def _sys001(snapshot: GraphSnapshot, design_ids) -> list[Violation]:  # noqa: ANN001
    """SYS001: a `frob:channel/boundary/secret` directive names a construct id
    that does not exist in the loaded design model -- a dangling reference,
    same posture as DRIFT002.

    Suppressed entirely when any `.strata` design file failed to load
    (`design_ids.errors`): construct ids are merged across every design
    file with no per-file provenance, so a failed sibling file's would-be
    ids are indistinguishable from a genuinely dangling reference -- fail
    toward the honest `SYS004` diagnostic (`sys_gate`), not a misleading
    SYS001 (reviewer-caught, T-0080 REJECT round 1: a single malformed
    design file was making every directive referencing its ids look
    dangling)."""
    if design_ids.errors:
        _log.debug(
            "SYS001: suppressed, %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []
    valid = {
        EdgeKind.CHANNEL: design_ids.channels,
        EdgeKind.BOUNDARY: design_ids.boundaries,
        EdgeKind.SECRET: design_ids.secrets,
    }
    return [
        v
        for edge in snapshot.edges
        if edge.kind in _SYS_DIRECTIVE_KINDS
        for v in (_sys001_check_edge(edge, valid),)
        if v is not None
    ]


def _sys001_check_edge(
    edge: Edge, valid: dict[EdgeKind, frozenset[str]]
) -> Violation | None:
    """The SYS001 `Violation` for one `frob:channel/boundary/secret` edge,
    or None when its target resolves in the loaded design model."""
    if edge.target in valid[edge.kind]:
        return None
    file, line = _site_from_edge_origin(edge.origin)
    _log.debug("SYS001: %s -> %s not in design model", edge.src, edge.target)
    return Violation(
        rule="SYS001",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"SYS001: frob:{edge.kind.value} {edge.target} at {edge.src} "
            f"does not name a {_SYS_DIRECTIVE_KINDS[edge.kind]} construct "
            f"in the loaded design model; fix the id or add it to the "
            f".strata design"
        ),
    )


def _sys003_one_model(model, root: Path) -> list[Violation]:  # noqa: ANN001
    """SYS003 violations from one design model's tier-2 code-binding
    conformance check (`bind_code` + `check_import_conformance`); an
    ambiguous binding within this model is logged and skipped, never fatal
    to the whole gate (a model's `code=` globs are scoped to its own
    nodes, so ambiguity here is a design-file bug, not a cross-model
    concern)."""
    from frob.strata import bind_code, check_import_conformance

    bound = bind_code(model, root)
    if bound.is_err:
        _log.warning("SYS003: code binding ambiguous, skipping: %s", bound.danger_err)
        return []
    report = check_import_conformance(model, bound.danger_ok, root)
    return [
        Violation(
            rule="SYS003",
            severity=Severity.WARN,
            file=violation.file,
            line=violation.line,
            message=(
                f"SYS003: undeclared cross-component import {violation.spec} at "
                f"{violation.file}:{violation.line} ({violation.src_component} -> "
                f"{violation.dst_component}); declare a Flow in that direction or "
                f"remove the import"
            ),
        )
        for violation in report.violations
    ]


def _sys003(design_ids, root: Path) -> list[Violation]:
    """SYS003: an in-repo import crosses two design-bound files with no
    declared `Flow` in that direction (docs/strata/surface.md#code-binding-
    tier-2-v0-implementation's "not yet wired" SYS-gate surfacing, T-0080).
    Runs once per successfully elaborated design model."""
    violations: list[Violation] = []
    for model in design_ids.models:
        violations.extend(_sys003_one_model(model, root))
    return violations


def _sys002(snapshot: GraphSnapshot, design_ids) -> list[Violation]:  # noqa: ANN001
    """SYS002: a boundary or secret construct in the design model has no
    `frob:boundary`/`frob:secret` code binding anywhere -- the construct
    exists on paper but nothing in code attests it (docs/strata/surface.md
    #directives-t-0080). Detection is `frob.strata._design_load.
    unbound_constructs`, imported lazily here (not at module top) for the
    same reason `_sys003_one_model` does: a repo with no design dir must
    never pay `frob.strata`'s `strata_core` native-extension import cost
    (T-0135) -- shared with `frob.strata.plan_obligations`'s "unbound"
    frontier so the join lives in exactly one place (T-0084 review
    finding 1)."""
    from frob.strata import unbound_constructs

    violations: list[Violation] = []
    for kind, construct_id in unbound_constructs(design_ids, snapshot):
        _log.debug("SYS002: %s %s has no code binding", kind.value, construct_id)
        violations.append(
            Violation(
                rule="SYS002",
                severity=Severity.WARN,
                file=f"design/{kind.value}/{construct_id}",
                line=0,
                message=(
                    f"SYS002: {kind.value} {construct_id} has no code binding; "
                    f"add: frob:{kind.value} {construct_id} at the enforcing site"
                ),
            )
        )
    return violations


_CLAIMS_RE = re.compile(r"<!--\s*frob:claims\s+(?P<view>\S+)\s*-->")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_INLINE_CODE_SPAN_RE = re.compile(r"`[^`]*`")


def _strip_inline_code_spans(line: str) -> str:
    """Blank out every inline `code span` on `line` (paired single
    backticks), preserving column positions so line/column reporting
    elsewhere never has to know this ran. A directive quoted inside
    backticks -- the natural way to DOCUMENT the directive in prose --
    must never be mistaken for a live claim (reviewer-caught, T-0085
    round 2)."""
    return _INLINE_CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)


# frob:ticket T-0085
def _claims_markers(root: Path) -> list[tuple[str, int, str]]:
    """Every `<!-- frob:claims <view> -->` doc marker under the doclink
    doc set (T-0085, docs/strata/threat.md#the-exhaustiveness-proof-the-
    point): `(file, line, view)`, reusing `doclink_gate`'s own `include`/
    `exclude`/`roots` config so the claims scan and the doc-obligation
    scan never disagree about which files are docs (charter: no
    duplication).

    Fence- and inline-code-aware (reviewer-caught, T-0085 round 2): a
    marker written to DOCUMENT the directive -- inside a fenced ```/~~~
    block, or inside inline `backticks` on the same line -- is prose
    ABOUT the directive, not a live claim, and must never be extracted.
    Fence state is a simple line-by-line open/close toggle (a line
    starting with three-or-more backticks or tildes, ignoring leading
    whitespace, flips it); inline spans are blanked out before matching
    so a marker can still be found elsewhere on the same line outside any
    span. A single unmatched inline backtick that never closes on the
    same line does not affect fence state -- CommonMark inline code spans
    never cross a line boundary."""
    include, exclude, roots = _doclink_config(root)
    paths = _obligated_docs(root, include, exclude) | set(roots)
    found: list[tuple[str, int, str]] = []
    for rel in sorted(paths):
        found.extend(_claims_markers_in_file(root, rel))
    return found


def _claims_markers_in_file(root: Path, rel: str) -> list[tuple[str, int, str]]:
    """Every live (non-fenced, non-inline-code) `frob:claims` marker in one
    doc file, as `(rel, line, view)` triples."""
    path = root / rel
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: list[tuple[str, int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line) is not None:
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _CLAIMS_RE.search(_strip_inline_code_spans(line))
        if match is not None:
            found.append((rel, lineno, match.group("view")))
    return found


# frob:ticket T-0085
def _doc003_violation(rel: str, lineno: int, message: str) -> Violation:
    """Build one DOC003 error `Violation` -- every failure mode is the same shape."""
    return Violation(
        rule="DOC003", severity=Severity.ERROR, file=rel, line=lineno, message=message
    )


# frob:ticket T-0085
def _doc003_one_marker(model, rel: str, lineno: int, view: str) -> Violation | None:  # noqa: ANN001
    """One `frob:claims <view>` marker's DOC003 outcome: `None` (proved),
    an unknown-view error, or a not-proved error naming the failing
    obligations."""
    from frob.strata import audit_claim

    result = audit_claim(model, view)
    if result.is_err:
        return _doc003_violation(
            rel,
            lineno,
            f"DOC003: frob:claims {view!r} names an unknown baseline view "
            f"({result.danger_err.value}); fix the view name",
        )
    audit = result.danger_ok
    if audit.proved:
        return None
    named = "; ".join(
        f"{v.rule} {v.cwe or v.capability or ''}: {v.detail}".strip()
        for v in audit.violations
    )
    return _doc003_violation(
        rel,
        lineno,
        f"DOC003: frob:claims {view!r} is not a PROVED exhaustiveness result "
        f"against the design model -- failing obligation(s): {named}",
    )


# frob:ticket T-0085
# DOC003: a `frob:claims <view>` doc marker whose view is not PROVED (zero
# THREAT001/THREAT002/THREAT003 violations) against the current design
# model is an error naming the failing obligations (docs/strata/threat.md
# #the-exhaustiveness-proof-the-point: "a README claiming 'protected
# against the OWASP Top 10' must cite a PROVED exhaustiveness result or it
# fails CI"). DOC002 is already taken (anchor resolution, T-0127), hence
# DOC003 for the claims audit (charter drift noted in docs/strata/threat.md).
def _doc003(root: Path, design_ids) -> list[Violation]:  # noqa: ANN001
    """DOC003: see the comment above. Suppressed when any design file
    failed to load (same posture as SYS001) -- a claim cannot be honestly
    evaluated against a partially loaded model. Runs no doc I/O at all when
    no `frob:claims` marker exists anywhere."""
    markers = _claims_markers(root)
    if not markers:
        return []
    if design_ids.errors:
        _log.debug(
            "DOC003: suppressed, %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []

    from frob.strata import merge_models

    model = merge_models(design_ids.models)
    violations = [
        v
        for rel, lineno, view in markers
        if (v := _doc003_one_marker(model, rel, lineno, view)) is not None
    ]
    return violations


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0080
# frob:ticket T-0085
# frob:tests tests/test_gates.py::TestSysGate.test_noop_no_design_dir
# frob:tests tests/test_gates.py::TestSysGate.test_sys001_dangling
# frob:tests tests/test_gates.py::TestSysGate.test_sys001_valid
# frob:tests tests/test_gates.py::TestSysGate.test_sys002_unbound
# frob:tests tests/test_gates.py::TestSysGate.test_sys002_bound
# frob:tests tests/test_gates.py::TestSysGate.test_sys003_import
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_load_failure
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_suppresses_sys001
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_proved_claim_passes
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_refutes_names_obligations
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_unclaimed_view_ignored
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_unknown_view
# sys_gate is opt-in via a `design/` (or `[strata].design_dir`) directory of
# `.strata` files existing, same posture as `decisions_gate`: a repo not yet
# using strata sees nothing. The `frob.strata` import is deferred until
# AFTER the directory check (T-0135): `frob.strata` transitively imports
# `_facts.py`, which needs the `strata_core` native extension, so a repo
# with no `design/` dir at all must never pay that import cost -- a
# standalone (`uv tool install frob`, no natives) install must not crash
# `frob check` on every repo, only degrade (T-0134) on repos that actually
# opted into `design/`.
def sys_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """SYS001 (dangling directive), SYS002 (unbound boundary/secret), SYS003
    (undeclared cross-component import, tier-2 conformance), and SYS004 (a
    `.strata` design file failed to parse/elaborate -- suppresses SYS001
    for the whole run since ids are merged across files with no per-file
    provenance). See the comment above for the opt-in/deferred-import
    posture."""
    root = Path(root)
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        _log.debug("sys_gate: no %s/ directory, skipping", design_dir)
        return ()

    from frob.strata import load_design_ids

    design_ids = load_design_ids(root, design_dir)
    violations = (
        *_sys004(design_ids, root),
        *_sys001(snapshot, design_ids),
        *_sys002(snapshot, design_ids),
        *_sys003(design_ids, root),
        *_doc003(root, design_ids),
    )
    _log_sys_gate_summary(design_ids, violations)
    return violations


def _log_sys_gate_summary(design_ids, violations: tuple[Violation, ...]) -> None:  # noqa: ANN001
    """Log `sys_gate`'s per-run summary: construct counts, violation count,
    and design load error count."""
    _log.info(
        "sys_gate: %d channel(s)/%d boundary(ies)/%d secret(s) in model, "
        "%d violation(s), %d design load error(s)",
        len(design_ids.channels),
        len(design_ids.boundaries),
        len(design_ids.secrets),
        len(violations),
        len(design_ids.errors),
    )


def _dup_config(root: Path) -> tuple[bool, float, bool]:
    """`([dup].enforce, [dup].threshold, [dup].region_kernel)` from frob.toml,
    defaulting to off/0.85/off.

    `region_kernel` gates the R1.5 exact-region kernel (`frob.dup.
    DupConfig.region_kernel_enabled`) independently of `enforce` -- turning
    on the whole-symbol rung ladder does not by itself pay for the extra
    suffix-array pass; both knobs must be true for R1.5 to run in the gate
    path.
    """
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False, 0.85, False
    try:
        with toml_path.open("rb") as fh:
            dup_cfg = tomllib.load(fh).get("dup", {})
        return (
            bool(dup_cfg.get("enforce", False)),
            float(dup_cfg.get("threshold", 0.85)),
            bool(dup_cfg.get("region_kernel", False)),
        )
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        _log.warning("dup_gate: frob.toml unreadable: %s", exc)
        return False, 0.85, False


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0001
# frob:waive TEST005 reason="dup_gate 52.2% branch cover, debt T-0160"
def dup_gate(root: Path, snapshot: GraphSnapshot, diff) -> tuple[Violation, ...]:  # noqa: ANN001
    """DUP001/DUP002: the diff introduces a clone of an existing symbol.

    Opt-in via `[dup].enforce = true` in frob.toml (default off): smart
    clone detection needs the frob-core native extension, so it stays
    silent until a repo turns it on. If enforce is on but frob-core is
    absent, emits one advisory note rather than failing.
    """
    from frob.dup import core_available

    root = Path(root)
    enforce, threshold, region_kernel = _dup_config(root)
    if not enforce:
        _log.debug("dup_gate: [dup].enforce off, skipping")
        return ()
    if not core_available():
        _log.warning("dup_gate: frob-core not installed; DUP rules skipped")
        return ()

    violations = _dup_gate_violations(snapshot, diff, threshold, region_kernel)
    _log.info("dup_gate: %d clone violation(s)", len(violations))
    return violations


def _dup_gate_violations(
    snapshot: GraphSnapshot,
    diff,
    threshold: float,
    region_kernel: bool,  # noqa: ANN001
) -> tuple[Violation, ...]:
    """Run `find_clones` and return the DUP001/DUP002 violations against
    the diff's touched refs, or empty (already logged) if clone-finding
    itself fails."""
    from frob.dup import DUP001, DUP002, DupConfig, find_clones
    from frob.dup import touched_refs as _touched

    report_result = find_clones(
        snapshot,
        DupConfig(threshold=threshold, region_kernel_enabled=region_kernel),
        diff=diff,
    )
    if report_result.is_err:
        _log.warning("dup_gate: find_clones failed: %s", report_result.danger_err)
        return ()
    report = report_result.danger_ok
    touched = _touched(snapshot, diff)
    return (
        *DUP001(report, touched, threshold),
        *DUP002(report, touched, threshold),
    )


def _current_version(root: Path) -> str | None:
    """The project version from pyproject.toml, or None if undetectable."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    version = data.get("project", {}).get("version")
    return version if isinstance(version, str) else None


def _changelog_mentions(root: Path, version: str) -> bool:
    """Whether CHANGELOG.md (if present) names `version`; absent file passes."""
    for name in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"):
        path = root / name
        if path.exists():
            try:
                return version in path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return True
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


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0003
# frob:waive TEST005 reason="release_gate 82.4% branch cover, debt T-0160"
def release_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """REL001: the public-API change since the last `frob release stamp`
    demands a version bump the declared version does not cover, or the
    changelog does not mention the version.

    Opt-in: runs only when a `.frob-release.json` manifest exists.
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

    bump, violations = _rel001_version(
        manifest_result.danger_ok, snapshot, current_version
    )
    if bump != 0 and not _changelog_mentions(root, current_version):
        violations.append(_rel001_missing_changelog(current_version))
    _log.info("release_gate: bump=%s, %d violation(s)", bump.name, len(violations))
    return tuple(violations)


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


def _fuzz_enforce(root: Path):  # noqa: ANN202
    """The `[fuzz].enforce` value from frob.toml as a `FuzzEnforce`, default OFF."""
    from frob.fuzz import FuzzEnforce

    enforce = FuzzEnforce.OFF
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                raw = tomllib.load(fh).get("fuzz", {}).get("enforce")
            if raw in tuple(FuzzEnforce):
                enforce = FuzzEnforce(raw)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("fuzz_gate: frob.toml unreadable: %s", exc)
    return enforce


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0002
def fuzz_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """FUZZ001/002/003 over the [fuzz] policy in frob.toml.

    Default enforce is OFF (a repo opts in): fuzzing is a strong mandate, so
    it stays silent until [fuzz].enforce is set -- the warn-first adoption
    posture.
    """
    from frob.fuzz import FuzzEnforce, FuzzPolicy, obligations

    root = Path(root)
    enforce = _fuzz_enforce(root)
    if enforce == FuzzEnforce.OFF:
        _log.debug("fuzz_gate: [fuzz].enforce=off, skipping")
        return ()

    obs = obligations(snapshot, FuzzPolicy(enforce=enforce))
    violations = _fuzz_gate_violations(root, snapshot, obs)
    _log.info("fuzz_gate: %d obligation(s), %d violation(s)", len(obs), len(violations))
    return violations


def _fuzz_gate_violations(
    root: Path, snapshot: GraphSnapshot, obs
) -> tuple[Violation, ...]:  # noqa: ANN001
    """FUZZ001/002/003 for the resolved fuzz `obs` obligations."""
    from frob.fuzz import (
        FUZZ001,
        FUZZ002,
        FUZZ003,
        load_fuzz_stamp,
        resolve_param_types,
    )

    param_types = {ob.ref: resolve_param_types(root, ob.ref) for ob in obs}
    stamp = load_fuzz_stamp(root)
    return (
        *FUZZ001(snapshot, obs),
        *FUZZ002(obs, param_types),
        *FUZZ003(snapshot, obs, stamp),
    )


_MD_LINK_RE = re.compile(r"\]\(([^)#\s]+)")
# Backtick path references (`docs/x.md`) count as links too: these docs are
# written terminal-first, where an index names files in code spans rather
# than markdown links -- an index entry is a link either way.
_MD_CODE_REF_RE = re.compile(r"`([^`\s]+\.md)`")


def _doclink_config(root: Path) -> tuple[list[str], list[str], list[str]]:
    """`(include, exclude, roots)` globs for doclink, with frob.toml overrides."""
    include = ["docs/**/*.md"]
    exclude: list[str] = []
    roots = ["docs/index.md", "README.md"]
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                section = tomllib.load(fh).get("gates", {}).get("docs", {})
            include = list(section.get("include", include))
            exclude = list(section.get("exclude", exclude))
            roots = list(section.get("roots", roots))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("doclink: frob.toml unreadable: %s", exc)
    return include, exclude, roots


def _obligated_docs(root: Path, include: list[str], exclude: list[str]) -> set[str]:
    """The set of doc files matched by `include` and not `exclude`."""

    obligated: set[str] = set()
    for glob in include:
        # frob:waive WALK001 reason="pathlib Path.glob's ** (zero-or-more-dirs) semantics matter here (e.g. default docs/**/*.md must match a top-level docs/orphan.md) and fnmatch.fnmatch (frob.excludes.is_excluded) does not have that semantics, so this cannot be reduced to an iter_files(suffix=...) prefilter without changing which docs are obligated; include is config-driven and defaults to the small docs/ subtree, not a repo-wide walk"  # noqa: E501
        for path in root.glob(glob):
            rel = path.relative_to(root).as_posix()
            if not any(fnmatch.fnmatch(rel, ex) for ex in exclude):
                obligated.add(rel)
    return obligated


def _linked_from_edges(snapshot: GraphSnapshot) -> set[str]:
    """Docs directly linked by a `frob:describes` anchor or `frob:doc` edge."""
    linked: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.DESCRIBES:
            linked.add(edge.src.split("#", 1)[0])
        elif edge.kind == EdgeKind.DOC:
            linked.add(edge.target.split("#", 1)[0])
    return linked


def _crawl_reachable(
    root: Path, roots: list[str], linked: set[str], obligated: set[str]
) -> set[str]:
    """Grow `linked` by crawling relative markdown links from the roots outward."""
    ordered_linked = sorted(linked)
    queue = [r for r in roots if (root / r).exists()]
    queue.extend(ordered_linked)
    seen: set[str] = set()
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        current_path = root / current
        if not current_path.exists():
            continue
        try:
            text = current_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        base = PurePosixPath(current).parent
        targets = _MD_LINK_RE.findall(text) + _MD_CODE_REF_RE.findall(text)
        for target in targets:
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = str(PurePosixPath(*(base / target).parts)).replace("../", "")
            for candidate in (resolved, target.lstrip("./")):
                if candidate in obligated and candidate not in seen:
                    linked.add(candidate)
                    queue.append(candidate)
    return linked


def _doclink_root_hint(root: Path, roots: list[str]) -> str:
    """Build the DOC001 'link it from X' hint against a root that actually exists.

    Blindly naming `roots[0]` (default `docs/index.md`) is wrong in repos
    that never created a docs index -- the hint pointed at a path that did
    not exist (T-0231, observed 256x in a sibling repo with no
    docs/index.md). Prefer the first configured root that exists on disk;
    if none do, suggest creating the first configured root instead of
    pretending it is already there.
    """
    for candidate in roots:
        if (root / candidate).exists():
            return f"link it from {candidate}"
    if roots:
        return (
            f"link it from {roots[0]} (create it -- no configured docs root exists yet)"
        )
    return "link it from a docs root (none configured -- see [gates.docs].roots)"


# frob:ticket T-0021
# frob:ticket T-0028
# frob:ticket T-0231
# frob:doc docs/modules/gates.md#public-api
def doclink_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC001: a doc file nothing links to is an error -- orphan docs rot.

    The obligated set is discovered by GLOB (default `docs/**/*.md`,
    `[gates.docs] include/exclude` in frob.toml), so a newly added doc file
    is automatically covered the moment it exists. A doc counts as linked
    when it carries a frob:describes anchor, is the target of a frob:doc
    edge, or is reachable through relative markdown links crawled from the
    root set (default docs/index.md and README.md).
    """
    root = Path(root)
    include, exclude, roots = _doclink_config(root)
    obligated = _obligated_docs(root, include, exclude)
    if not obligated:
        _log.debug("doclink: no docs matched %s", include)
        return ()
    linked = _crawl_reachable(root, roots, _linked_from_edges(snapshot), obligated)
    orphans = sorted(obligated - linked - set(roots))

    link_hint = _doclink_root_hint(root, roots)
    violations = tuple(_doc001_orphan(orphan, link_hint) for orphan in orphans)
    _log.info("doclink: %d obligated, %d orphaned", len(obligated), len(violations))
    return violations


# frob:waive DUP001 reason="dup grouped this with frob.vet._scan's \
# _vet004_violation purely on generic Violation(...)-builder shape; \
# different gate family (doc-graph vs dependency-vet), unrelated rules"
def _doc001_orphan(orphan: str, link_hint: str) -> Violation:
    """DOC001: `orphan` is a doc file linked from nowhere."""
    return Violation(
        rule="DOC001",
        severity=Severity.ERROR,
        file=orphan,
        line=0,
        message=(
            f"DOC001: {orphan} is linked from nowhere; add a "
            f"frob:describes anchor, reference it with frob:doc, or "
            f"{link_hint}"
        ),
    )


_ANCHOR_ID_RE = re.compile(r'<a\s+id="([^"]+)"')
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _doc_anchor_slugs(path: Path) -> Option[set[str]]:
    """Every resolvable slug in a doc file: heading slugs plus explicit `<a id>`s.

    `Nothing` means the file could not be read at all (missing or IO error),
    distinct from `Some(set())` (a real, empty doc).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return Nothing()
    seen: dict[str, int] = {}
    slugs = {
        dedupe_slug(slugify(heading.group(2)), seen)
        for heading in _MD_HEADING_RE.finditer(text)
    }
    slugs.update(m.group(1) for m in _ANCHOR_ID_RE.finditer(text))
    return Some(slugs)


# frob:doc docs/modules/gates.md#public-api
def _anchor_mismatch_message(
    target: str, docfile: str, slug: str, slugs: set[str]
) -> str:
    """Build the DOC002 unresolved-anchor message: the computed slug, the
    anchors actually found in the target file, and the nearest match by
    edit distance (via `difflib.get_close_matches`) so a `frob:doc` author
    does not have to guess a GitHub-style slug by hand."""
    found = ", ".join(sorted(slugs)) if slugs else "(none)"
    nearest = difflib.get_close_matches(slug, slugs, n=1, cutoff=0.0)
    suggestion = f"; did you mean #{nearest[0]}?" if nearest else ""
    return (
        f"DOC002: frob:doc anchor {target!r} does not resolve; computed "
        f"slug #{slug} does not match any anchor in {docfile} "
        f"(found: {found}){suggestion}"
    )


def _docanchor_violation(rule_file: str, line: int, message: str) -> Violation:
    """Build one DOC002 error `Violation` -- every failure mode is the same shape."""
    return Violation(
        rule="DOC002",
        severity=Severity.ERROR,
        file=rule_file,
        line=line,
        message=message,
    )


# frob:doc docs/modules/gates.md#public-api
def docanchor_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC002: a `frob:doc` edge whose target anchor does not resolve is an error.

    Every `frob:doc <file>#<slug>` target must resolve: `<file>` must exist
    under `root`, and `<slug>` must be either a GitHub-style heading slug
    (`frob.graph.dsl.slugify`, the same slugifier `markdown_anchors` uses)
    or an explicit `<a id="...">` anchor in that file -- the second form is
    how docs/modules/dup.md and docs/modules/arch.md give several models a
    stable anchor under one heading.

    `root` here must be the repo root, not a scoped check path (T-0314):
    `<file>` in a `frob:doc` directive is always repo-relative text, so a
    scoped `frob check <subdir>` run that fed the scoped subdir in as
    `root` rebased every target path and reported a spurious DOC002 on
    every directive. `run_gates` passes `st.repo_root` here for exactly
    this reason -- see `_GateInputs.repo_root`.
    """
    root = Path(root)
    slug_cache: dict[str, Option[set[str]]] = {}
    violations = [
        v
        for edge in snapshot.edges
        if edge.kind == EdgeKind.DOC
        for v in (_docanchor_check_edge(root, edge, slug_cache),)
        if v is not None
    ]
    _log.info("docanchor: %d violation(s)", len(violations))
    return tuple(violations)


def _docanchor_check_edge(
    root: Path, edge: Edge, slug_cache: dict[str, Option[set[str]]]
) -> Violation | None:
    """The DOC002 `Violation` for one `frob:doc` edge, or None when its
    `<file>#<slug>` target resolves. `slug_cache` memoizes `_doc_anchor_slugs`
    per doc file across the whole gate run."""
    origin_file, _, lineno_text = edge.origin.rpartition(":")
    line = int(lineno_text) if lineno_text.isdigit() else 0
    origin_file = origin_file or edge.origin
    target = edge.target
    if "#" not in target:
        return _docanchor_violation(
            origin_file,
            line,
            f"DOC002: frob:doc target {target!r} has no #anchor; use <file>#<slug>",
        )
    docfile, slug = target.split("#", 1)
    if docfile not in slug_cache:
        slug_cache[docfile] = _doc_anchor_slugs(root / docfile)
    slugs = slug_cache[docfile]
    if slugs.is_nothing:
        return _docanchor_violation(
            origin_file,
            line,
            f"DOC002: frob:doc target file {docfile!r} does not exist",
        )
    if slug not in slugs.danger_some:
        return _docanchor_violation(
            origin_file,
            line,
            _anchor_mismatch_message(target, docfile, slug, slugs.danger_some),
        )
    return None


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
# frob:waive TEST005 reason="perf_gate 85.7% branch cover, debt T-0160"
def perf_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PERF001..PERF004, run at the policy/gates stage per docs/modules/perf.md's
    Integration points. Parses every scannable source file (see
    `_perf_gate_candidate_paths`) and hands the parsed set to
    `frob.perf.perf_rules` (same posture as `frob.policy`'s
    `_pattern_violations`: gates does the IO, `perf_rules` stays pure). A
    file whose extension SHOULD parse but fails still gets a visible skip
    message."""
    from frob.perf import perf_rules

    candidate_paths = _perf_gate_candidate_paths(snapshot)
    parsed = _perf_gate_parse_files(root, candidate_paths)
    violations = perf_rules(snapshot, parsed)
    _log.info(
        "perf_gate: %d file(s) scanned, %d violation(s)", len(parsed), len(violations)
    )
    return violations


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
        "perf",
        "fuzz",
        "release",
        "clones",
        "decisions",
        "sys",
        "secrets",
        "tickets",
        "archgate",
        "pii_structural",
        "refs",
        "registry",
        "docblocks",
        "walk_lint",
        "excludehazard",
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


def _load_diff(root: Path, base: str) -> Diff:
    """The working diff against `base`, degrading to an empty diff on failure.

    A missing diff (fresh repo, unknown base, detached HEAD) must not skip the
    whole gates stage -- only coverage/scope read it, so the diff-dependent
    gates simply see no touched symbols.
    """
    diff_result = working_diff(root, base)
    if diff_result.is_err:
        _log.warning(
            "run_gates: working_diff failed (%s); diff-dependent gates see no "
            "touched set",
            diff_result.danger_err,
        )
        return Diff(base=base, hunks=())
    return diff_result.danger_ok


def _load_tests(root: Path) -> CollectedTests:
    """Collected pytest + cargo node ids, degrading each collector independently
    to an empty set on failure (a missing/broken toolchain must not halt the
    whole gates run -- but see `_cov003`: an evidence id that consequently
    fails to resolve becomes a loud violation, never a silent pass, T-0102)."""
    node_ids: set[str] = set()

    python_result = collect_python_tests(root)
    if python_result.is_err:
        _log.error("run_gates: pytest collection failed: %s", python_result.danger_err)
    else:
        node_ids.update(python_result.danger_ok.node_ids)

    rust_result = collect_rust_tests(root)
    if rust_result.is_err:
        _log.error("run_gates: cargo collection failed: %s", rust_result.danger_err)
    else:
        node_ids.update(rust_result.danger_ok.node_ids)

    return CollectedTests(node_ids=frozenset(node_ids))


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
    return _GateInputs(
        root=root,
        repo_root=_repo_root_for(root),
        cfg=cfg,
        snapshot=snapshot,
        queue=queue,
        lock=lock,
        diff=_load_diff(root, cfg.base),
        tests=_load_tests(root),
        invariants=invariants,
        rules=tuple(rules),
        rule_ids=frozenset(r.id for r in rules),
        coverage=coverage,
        test_policy=test_policy,
        systems=systems,
        ticket=ticket,
        sweep=sweep,
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
    {"archgate", "sys", "clones", "perf", "pii_structural", "secrets"}
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
    "perf",
    "fuzz",
    "release",
    "clones",
    "decisions",
    "sys",
    "secrets",
    "tickets",
    "archgate",
    "pii_structural",
    "refs",
    "registry",
    "docblocks",
    "walk_lint",
    "excludehazard",
    "scope",
    "prework",
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
def _build_jobs(
    selected: frozenset[str], st: _GateInputs
) -> tuple[
    dict[str, Callable[[], tuple[Violation, ...]]],
    dict[str, _ProcessJob],
    list[str],
]:
    """Map each selected gate name to a job over the loaded state: a zero-arg
    thread-pool closure for I/O-bound/cheap gates, or a `_ProcessJob`
    (T-0415) for the CPU-bound giants in `_PROCESS_POOL_GATES`."""
    from frob.policy import policy_gate

    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {
        "drift": lambda: drift_gate(st.snapshot, st.lock),
        "coverage": lambda: coverage_gate(
            st.repo_root, st.snapshot, st.queue, st.diff, st.tests
        ),
        "invariant": lambda: (
            *invariant_gate(st.invariants, st.snapshot, st.tests, st.rule_ids),
            *inv003_gate(st.repo_root, st.invariants),
            *inv004_gate(st.repo_root),
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
        # T-0436: fenced-code-block doc-drift heuristic, repo_root-scoped for
        # the same reason docanchor/refs are -- doc paths are repo-relative
        # text either way, and `git ls-files *.md` must see the whole repo.
        "docblocks": lambda: doc004_gate(st.repo_root, st.snapshot),
        "fuzz": lambda: fuzz_gate(st.root, st.snapshot),
        "release": lambda: release_gate(st.root, st.snapshot),
        "decisions": lambda: decisions_gate(st.root, st.snapshot),
        "tickets": lambda: tickets_gate(st.root, st.queue),
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
        # T-0343: fail-closed exhaustiveness drift-lock over
        # docs/design/registry/*.yaml -- known_rules is this run's live
        # gate-rule-id + policy-rule-id union, never a hardcoded list, so
        # handled_by:<rule-id> is verified against what this build
        # actually enforces.
        "registry": lambda: registry_gate(
            st.repo_root, st.queue, _KNOWN_GATE_RULES | st.rule_ids
        ),
    }
    process_jobs: dict[str, _ProcessJob] = {
        "perf": _ProcessJob(perf_gate, (st.root, st.snapshot)),
        "clones": _ProcessJob(dup_gate, (st.root, st.snapshot, st.diff)),
        "sys": _ProcessJob(sys_gate, (st.root, st.snapshot)),
        "secrets": _ProcessJob(secrets_gate, (st.root,)),
        "archgate": _ProcessJob(arch_gate, (st.root,)),
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
    }
    selected_thread = {
        name: job for name, job in thread_jobs.items() if name in selected
    }
    selected_process = {
        name: job for name, job in process_jobs.items() if name in selected
    }
    ticket_jobs, skipped = _build_ticket_scoped_jobs(selected, st)
    selected_thread.update(ticket_jobs)
    return selected_thread, selected_process, skipped


def _build_ticket_scoped_jobs(
    selected: frozenset[str], st: _GateInputs
) -> tuple[dict[str, Callable[[], tuple[Violation, ...]]], list[str]]:
    """`scope`/`prework` jobs: both need `st.ticket`, so both are skipped
    (not run, not failed) rather than registered when no ticket is active."""
    jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {}
    skipped: list[str] = []
    if "scope" in selected:
        scope_ticket = st.ticket
        if scope_ticket is not None:
            jobs["scope"] = lambda: scope_gate(
                st.diff, scope_ticket, st.snapshot, root=st.root, queue=st.queue
            )
        else:
            skipped.append("scope")
    if "prework" in selected:
        pre_ticket = st.ticket
        if pre_ticket is not None:
            jobs["prework"] = lambda: prework_gate(pre_ticket, st.snapshot, st.sweep)
        else:
            skipped.append("prework")
    return jobs, skipped


# frob:ticket T-0232
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


# frob:ticket T-0415
def _run_process_gate(
    func: Callable[..., tuple[Violation, ...]], args: tuple
) -> tuple[tuple[Violation, ...], float]:
    """Picklable `ProcessPoolExecutor` entry point (T-0415): run one
    CPU-bound gate (`func(*args)`) in its own worker process and return its
    own `time.process_time()` -- accurate here (unlike a shared thread pool,
    T-0232) because each worker process runs exactly one job, so there is no
    sibling job to contend with for CPU. Must stay a module-level function
    (not a closure/lambda) so `pickle` can address it by `__module__` +
    `__qualname__` when the parent ships the call to a worker."""
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


# frob:ticket T-0415
def _submit_process_pool(
    ppool: ProcessPoolExecutor,
    process_jobs: dict[str, _ProcessJob],
    raw: dict[str, tuple[Violation, ...]],
    counts: dict[str, int],
    timing: dict[str, float],
) -> None:
    """Submit every `process_jobs` entry to `ppool` and drain the results
    into `raw`/`counts`/`timing` (T-0415) -- the process-pool half of
    `_run_combined_jobs`, split out to keep that function under ARCH001's
    line threshold."""
    process_futures = {
        name: ppool.submit(_run_process_gate, job.func, job.args)
        for name, job in process_jobs.items()
    }
    _drain_futures(process_futures, raw, counts, timing, pool_label=" (process pool)")


def _merge_canonical_order(raw: dict[str, tuple[Violation, ...]]) -> list[Violation]:
    """Flatten `raw` (gate name -> its violations) into one list ordered by
    `_CANONICAL_GATE_ORDER` (T-0415) -- the fixed order the old single-pool
    `_build_jobs` dict used, so output stays identical regardless of which
    pool produced a given gate's result first."""
    violations: list[Violation] = []
    for name in _CANONICAL_GATE_ORDER:
        if name in raw:
            violations.extend(raw[name])
    return violations


def _run_combined_jobs(
    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]],
    process_jobs: dict[str, _ProcessJob],
) -> tuple[list[Violation], dict[str, int], dict[str, float]]:
    """Run `thread_jobs` on a `ThreadPoolExecutor` and `process_jobs`
    (the CPU-bound giants, T-0415/docs/audits/perf.md H3) on a
    `ProcessPoolExecutor` at the same time, so e.g. archgate and sys
    actually overlap instead of GIL-serializing on one shared pool. Merges
    results back via `_merge_canonical_order` so output stays
    deterministic regardless of which pool finishes a job first."""
    counts: dict[str, int] = {}
    timing: dict[str, float] = {}
    raw: dict[str, tuple[Violation, ...]] = {}
    if not thread_jobs and not process_jobs:
        return [], counts, timing

    with ThreadPoolExecutor(max_workers=max(1, len(thread_jobs))) as tpool:
        thread_futures = {
            name: tpool.submit(_timed_job(job)) for name, job in thread_jobs.items()
        }
        if process_jobs:
            # Bounded worker count (constraint 4): never more workers than
            # jobs, never more than the machine's CPU count.
            proc_workers = max(1, min(len(process_jobs), os.cpu_count() or 4))
            with ProcessPoolExecutor(max_workers=proc_workers) as ppool:
                _submit_process_pool(ppool, process_jobs, raw, counts, timing)
        _drain_futures(thread_futures, raw, counts, timing, pool_label="")

    return _merge_canonical_order(raw), counts, timing


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0021
def run_gates(cfg: GateConfig) -> Result[GateReport, GateError]:
    """Load everything once, then run the selected gates in parallel and merge."""
    start_all = time.monotonic()
    selected = cfg.gates or _ALL_GATES
    _log.info(
        "run_gates: root=%s base=%s gates=%s", cfg.root, cfg.base, sorted(selected)
    )

    inputs_result = _load_inputs(cfg)
    if inputs_result.is_err:
        return Err(inputs_result.danger_err)
    st = inputs_result.danger_ok

    thread_jobs, process_jobs, skipped = _build_jobs(selected, st)
    report = _assemble_gate_report(
        cfg, st, thread_jobs, process_jobs, skipped, start_all
    )
    return Ok(report)


def _assemble_gate_report(
    cfg: GateConfig,
    st: _GateInputs,
    thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]],
    process_jobs: dict[str, _ProcessJob],
    skipped: list[str],
    start_all: float,
) -> GateReport:
    """Run `thread_jobs`/`process_jobs` (T-0415), fold in the WAIVE001/
    WAIVE002 self-checks, apply waivers and severity overrides, and log the
    run's final tally."""
    all_violations: list[Violation] = [
        *_waive001_violations(st.snapshot),
        *_waive002_violations(st.snapshot, st.rule_ids),
    ]
    job_violations, counts, timing = _run_combined_jobs(thread_jobs, process_jobs)
    counts["waive"] = len(all_violations)
    all_violations.extend(job_violations)
    # T-0470: WAIVE003 needs the full assembled violation set (it re-runs
    # `_match_waiver` per package-scoped violation to see how many distinct
    # packages one waiver reaches), so it runs after `job_violations` is
    # folded in, not alongside the other WAIVE00* self-checks above.
    all_violations.extend(_waive003_violations(tuple(all_violations), st.snapshot))

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
    "DecisionError",
    "GateConfig",
    "GateError",
    "GateReport",
    "GateStats",
    "Invariant",
    "InvariantError",
    "PreworkSweep",
    "Severity",
    "SystemSpec",
    "TestPolicy",
    "Violation",
    "WaiverRef",
    "active_ticket",
    "arch_gate",
    "coverage_gate",
    "delta_violations",
    "drift_gate",
    "exclude_hazard_gate",
    "inv003_gate",
    "inv004_gate",
    "invariant_gate",
    "is_baseline_stale",
    "load_baseline",
    "load_coverage",
    "load_invariants",
    "cve_fingerprint_scan_gate",
    "decisions_gate",
    "doclink_gate",
    "docanchor_gate",
    "dup_gate",
    "evidence_covers_scope",
    "fuzz_gate",
    "perf_gate",
    "pii_structural_gate",
    "release_gate",
    "prework_gate",
    "record_prework",
    "registry_gate",
    "run_gates",
    "scope_digest",
    "scope_gate",
    "secrets_gate",
    "stamp_baseline",
    "stamp_coverage",
    "sweep_ticket",
    "sys_gate",
    "test_gate",
    "violation_fingerprint",
    "walk_lint_gate",
]
