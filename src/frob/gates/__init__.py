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

import difflib
import fnmatch
import hashlib
import re
import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from pydantic import ValidationError
from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._baseline import (
    delta_violations,
    is_baseline_stale,
    load_baseline,
    stamp_baseline,
    violation_fingerprint,
)
from frob.gates._coverage import load_coverage, load_stamp, stamp_coverage
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
from frob.gates._prework import load_prework, record_prework
from frob.gates._secrets import secrets_gate
from frob.gates.invariants import Invariant, InvariantError, load_invariants
from frob.gitio import Diff, Hunk, current_branch, run_argv, working_diff
from frob.graph import (
    BuildError,
    Edge,
    EdgeKind,
    GraphSnapshot,
    build_graph,
    dedupe_slug,
    edges_from,
    slugify,
)
from frob.graph._models import LockFile
from frob.graph.lock import drift as _graph_drift
from frob.graph.lock import load_lock
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile
from frob.logging import get_logger
from frob.testing import CollectedTests, collect_python_tests, collect_rust_tests
from frob.tickets import Ticket, TicketQueue, TicketState, load_queue
from frob.tickets._models import CMD_EVIDENCE_ALLOWED_KINDS, is_cmd_evidence
from frob.tickets._provisional import is_draft_id, on_default_branch
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
    """`path::a.b` -> `path::a::b`, the pytest node id spelling of a qualname."""
    path, _, qualname = symref.partition("::")
    return f"{path}::{qualname.replace('.', '::')}"


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


def _is_test_file(path: str) -> bool:
    """True if `path` is itself a test file (documented duplicate of
    `frob.testing._select._is_test_file`'s name/dir heuristic, not importable
    in isolation since it is a private helper of that module)."""
    pure = PurePosixPath(path)
    if "tests" in pure.parts[:-1]:
        return True
    name = pure.stem
    return name.startswith("test_") or name.endswith("_test")


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


def _evidence_collected(evidence: str, tests: CollectedTests) -> bool:
    """Exact node-id membership, or bare-function match for parametrized
    tests (`f` satisfies evidence when only `f[param]` variants collect)."""
    if evidence in tests.node_ids:
        return True
    prefix = evidence + "["
    return any(node.startswith(prefix) for node in tests.node_ids)


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
    `#[cfg(test)] mod tests { ... }`, mirroring `_is_test_file`'s "tests" dir
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
    """
    valid: list[Edge] = []
    for e in edges:
        if _node_id_collected(_symref_to_nodeid(e.src), tests.node_ids):
            valid.append(e)
        elif (
            snapshot is not None
            and _is_native_test_src(e.src)
            and _is_native_test_symref(e.src)
            and e.src in snapshot.symbols
        ):
            valid.append(e)
    return valid


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
        "DRIFT001",
        "DRIFT002",
        "SCOPE001",
        "PRE001",
        "INV001",
        "INV002",
        "TEST001",
        "TEST002",
        "TEST003",
        "TEST004",
        "TEST005",
        "TEST006",
        "TEST007",
        "TEST008",
        "TODO001",
        "WAIVE001",
        "WAIVE002",
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
        "SYS001",
        "SYS002",
        "SYS003",
        "SYS004",
        "SEC001",
        "SEC002",
        "SEC003",
        "TICK001",
        "TICK002",
    }
)

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
_UNWAIVABLE_RULES = frozenset({"TEST008", "SEC003", "TICK001", "TICK002"})


def _unwaivable_channel_rules() -> frozenset[str]:
    """Rule/category ids from tool channels `frob:waive` can never reach.

    T-0101 decision (documented in docs/modules/gates.md#waive-boundary):
    honoring waivers in the `frob-arch` check stage would mean threading
    the waiver-matching machinery into `frob.check`'s Diagnostic pipeline
    (`analyze_project` produces `ArchSuggestion`s, never `Violation`s) --
    a bigger surface change than a WARN justifies today. Instead, a waiver
    that names one of `frob.arch`'s categories is flagged as ineffective
    rather than silently doing nothing.
    """
    from typing import get_args

    from frob.arch._models import ArchCategory

    return frozenset(get_args(ArchCategory))


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
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        if edge.target in known:
            continue
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
        violations.append(
            Violation(
                rule="WAIVE002",
                severity=Severity.WARN,
                file=file,
                line=0,
                message=(
                    f"WAIVE002: frob:waive on {edge.src} targeting "
                    f"'{edge.target}' is ineffective -- {detail}"
                ),
            )
        )
    return tuple(violations)


def _match_waiver(
    violation: Violation, waivers_by_rule: dict[str, list[Edge]]
) -> Edge | None:
    """The first WAIVE edge whose site matches `violation`, or None.

    Two modes, chosen by whether `violation.symref` is set (T-0148):

    - `violation.symref is not None` (currently only TEST005's per-symbol
      branch-coverage check): the violation is about exactly one symbol,
      so only an EXACT `waiver.src == violation.symref` counts -- a
      `frob:waive` placed above a *different* symbol, or bare at file
      top, does not match. Without this, placement above a specific
      symbol is cosmetic: `frob.graph.dsl`'s `_enclosing_src` still binds
      a `path::qualname` edge, but the old file-prefix comparison below
      stripped the `::qualname` back off before comparing, so one
      directive anywhere in a file silently waived every violation of
      that rule in the whole file (the blanket-waiver bug T-0148's
      review caught empirically: 102 file-top waivers absorbing 195
      distinct findings).
    - `violation.symref is None` (every other rule, plus TEST005's own
      per-module line-coverage and per-system checks, which have no
      single symbol to bind to): the original file-scoped match -- a
      waiver's `src` symbol/file equals the violation's `file` (either
      the bare path or a `path::qualname` symref rooted at that path).
      This is the CORRECT precision for those checks, not a shortcut:
      one module-line violation per file has exactly one natural site.

    `violation.rule in _UNWAIVABLE_RULES` (currently just TEST008) short-
    circuits to `None` regardless of any matching `frob:waive` edge --
    by construction, not by omission; see `_UNWAIVABLE_RULES`'s comment.

    T-0276: a THIRD mode covers package/system-level violations (TEST003/
    TEST004, whose `violation.file` is an interface id like
    `crates/foo/src` or a system id, never a real single file) -- a
    waiver written in any file living under that package prefix also
    counts. Without this, such a violation's waiver could never match
    ANYTHING: no real source file's path is ever literally equal to a
    directory-shaped interface id, so the plain file-scoped comparison
    below always failed by construction (found while investigating why a
    `frob:waive TEST003 reason="..."` sitting in a rust integration test
    file reported `0 waived` in feldspar's adoption sweep -- traced to
    this, not to any check_type-based exclusion of `.rs` directives,
    which does not exist: `frob.graph.build_graph`/`_load_tests` are
    check_type-agnostic).
    """
    if violation.rule in _UNWAIVABLE_RULES:
        return None
    candidates = waivers_by_rule.get(violation.rule, ())
    if violation.symref is not None:
        for waiver in candidates:
            if waiver.src == violation.symref:
                return waiver
        return None
    package_prefix = violation.file.rstrip("/") + "/"
    for waiver in candidates:
        waiver_file = waiver.src.split("::", 1)[0]
        if (
            waiver.src == violation.file
            or waiver_file == violation.file
            or waiver_file.startswith(package_prefix)
        ):
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
# Coverage: COV001..COV004 and TODO001
# ---------------------------------------------------------------------------


# frob:doc docs/modules/gates.md#public-api
def coverage_gate(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff, tests: CollectedTests
) -> tuple[Violation, ...]:
    """COV001..COV004 and TODO001."""
    violations: list[Violation] = []
    violations.extend(_cov001(snapshot))
    violations.extend(_cov002(snapshot, queue, diff))
    violations.extend(_cov003(queue, tests))
    violations.extend(_cov004(queue))
    violations.extend(_todo001(snapshot, queue, diff))
    return tuple(violations)


def _documented_srcs(snapshot: GraphSnapshot) -> set[str]:
    """Symrefs carrying an explicit `frob:doc` edge."""
    return {e.src for e in snapshot.edges if e.kind == EdgeKind.DOC}


def _cov001(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """COV001: a public symbol has no explicit `frob:doc` edge.

    A docstring is not enough -- the obligation is an explicit `frob:doc
    <docs/anchor>` directive tying the symbol to a doc page whose drift is
    then tracked. Explicit edges are the point: they are what DRIFT001 can
    check.
    """
    documented = _documented_srcs(snapshot)
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.symref in documented:
            continue
        if _is_test_path(record.id.path):
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
    """True if `path` matches any open ticket's scope glob."""

    return any(
        fnmatch.fnmatch(path, glob) for _tid, scope in open_scopes for glob in scope
    )


def _ticket_edges(snapshot: GraphSnapshot, symref: str) -> list[Edge]:
    """The `frob:ticket` edges anchored on `symref`."""
    return [e for e in edges_from(snapshot, symref) if e.kind == EdgeKind.TICKET]


def _bound_to_open_ticket(
    snapshot: GraphSnapshot, queue: TicketQueue, symref: str
) -> bool:
    """True if `symref` has a `frob:ticket` edge to an open ticket."""
    for edge in _ticket_edges(snapshot, symref):
        ticket = queue.tickets.get(edge.target)
        if ticket is not None and ticket.state in _OPEN_STATES:
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
    snapshot: GraphSnapshot, queue: TicketQueue, symref: str
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
    return _bound_to_open_ticket(snapshot, queue, module_symref)


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
    demanding a copy-pasted directive per declaration.
    """
    open_scopes = _open_scopes(queue)
    touched = sorted(_touched_symrefs(diff, snapshot))
    violations: list[Violation] = []
    for symref in touched:
        if _bound_to_open_ticket(snapshot, queue, symref):
            continue
        if _covered_by_strata_module(snapshot, queue, symref):
            _log.debug("COV002: %s covered by its .strata module's ticket edge", symref)
            continue
        record = snapshot.symbols[symref]
        if _scope_covers(record.id.path, open_scopes):
            _log.debug("COV002: %s covered by an open ticket's scope", symref)
            continue
        _log.debug("COV002: %s changed with no open ticket", symref)
        violations.append(
            Violation(
                rule="COV002",
                severity=Severity.ERROR,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"COV002: {symref} changed with no frob:ticket edge to an open "
                    f"ticket; run: frob ticket new, then add: frob:ticket <id>"
                ),
            )
        )
    return tuple(violations)


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
        for evidence in ticket.evidence:
            if _evidence_valid_for_ticket(evidence, ticket, tests):
                continue
            _log.debug("COV003: %s evidence %s not collected", ticket.id, evidence)
            if is_cmd_evidence(evidence):
                message = (
                    f"COV003: {ticket.id} evidence {evidence!r} is cmd: evidence "
                    f"but kind={ticket.kind.value!r} is not in "
                    f"{allowed_kinds}; fix the ticket's kind or replace with "
                    f"pytest --evidence node ids"
                )
            else:
                message = (
                    f"COV003: {ticket.id} evidence {evidence!r} does not resolve "
                    f"to a collected test; run: frob test --collect to refresh, "
                    f"or fix the evidence id"
                )
            violations.append(
                Violation(
                    rule="COV003",
                    severity=Severity.ERROR,
                    file=f"tickets/{ticket.id}",
                    line=0,
                    message=message,
                )
            )
    return tuple(violations)


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


def _todo001_edges(snapshot: GraphSnapshot, queue: TicketQueue) -> list[Violation]:
    """TODO001: `frob:todo` edges bound to a non-open (or missing) ticket."""
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TODO:
            continue
        target = queue.tickets.get(edge.target)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("TODO001: %s -> %s not open", edge.src, edge.target)
        violations.append(
            Violation(
                rule="TODO001",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"TODO001: frob:todo {edge.target} at {edge.src} is not bound to "
                    f"an open ticket; run: frob ticket new, then rebind"
                ),
            )
        )
    return violations


def _todo001_bare(snapshot: GraphSnapshot, diff: Diff) -> list[Violation]:
    """TODO001: bare TODO/FIXME comments in diff-touched, freshly parsed files."""
    from frob.lang import parse_file  # local import: keep gates' top import list lean

    root = Path(snapshot.root)
    touched = sorted(_touched_files(diff))
    violations: list[Violation] = []
    for file in touched:
        parsed = parse_file(root / file)
        if parsed.is_err:
            continue
        for comment in parsed.danger_ok.comments:
            for offset, line_text in enumerate(
                comment.text.splitlines() or [comment.text]
            ):
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
    """TODO001: `frob:todo` bound to a non-open ticket, or a bare TODO/FIXME comment
    in a diff-touched file (parsed fresh via `frob.lang`, cheap since scoped to the
    diff, not the whole tree)."""
    return (
        *_todo001_edges(snapshot, queue),
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
        if any(fnmatch.fnmatch(path, glob) for glob in scope)
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
        if any(fnmatch.fnmatch(file, glob) for glob in other.scope):
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
    violations: list[Violation] = []
    for file in touched:
        if any(fnmatch.fnmatch(file, glob) for glob in ticket.scope):
            continue
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
            continue
        _log.debug("SCOPE001: %s outside %s's scope", file, ticket.id)
        violations.append(
            Violation(
                rule="SCOPE001",
                severity=Severity.ERROR,
                file=file,
                line=0,
                message=(
                    f"SCOPE001: {file} is outside {ticket.id}'s declared scope; "
                    f"extend the ticket's scope or open a new ticket for this file"
                ),
            )
        )
    return tuple(violations)


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
    effective = len(valid) if edges else _inferred_unit_cases(record.symref, tests)
    leaf = _snake(record.id.qualname.rsplit(".", 1)[-1])
    if effective == 0 and not edges:
        _log.debug("TEST001: %s has no unit edge or convention match", record.symref)
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
    if effective < cfg.min_unit_cases:
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
    return None


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
    unit_edges = _test_edges(snapshot, "unit")
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or _is_test_file(record.id.path)
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
    """Every `src/<pkg>/<subpkg>` package that contains a public, non-test symbol."""
    packages: dict[str, bool] = {}
    for record in snapshot.symbols.values():
        if record.public and not _is_test_file(record.id.path):
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
    violations: list[Violation] = []
    for package in ordered_packages:
        valid = _valid_edges(_edges_for_package(all_pairs, package), tests, snapshot)
        if len(valid) < cfg.min_integration:
            _log.debug(
                "TEST003: %s has %d/%d integration edges",
                package,
                len(valid),
                cfg.min_integration,
            )
            violations.append(
                Violation(
                    rule="TEST003",
                    severity=Severity.WARN,
                    file=package,
                    line=0,
                    message=(
                        f"TEST003: interface {package} has {len(valid)} integration "
                        f"test(s), below min_integration={cfg.min_integration}; "
                        f'add: frob:tests {package} kind="integration"'
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
    violations: list[Violation] = []
    for consumer, provider in ordered_pairs:
        if _pair_covered(_consumer_leaf(consumer), provider, all_pairs, tests):
            continue
        _log.debug("TEST007: %s -> %s boundary untested", consumer, provider)
        violations.append(
            Violation(
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
        )
    return tuple(violations)


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
    """TEST005 per-symbol branch-coverage floor."""
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.kind not in (
            SymbolKind.FUNCTION,
            SymbolKind.METHOD,
        ):
            continue
        pct = data.symbol_branch.get(record.symref)
        if pct is not None and pct < cfg.unit_branch_cov:
            _log.debug(
                "TEST005: %s branch cov %.1f%% < %d%%",
                record.symref,
                pct,
                cfg.unit_branch_cov,
            )
            violations.append(
                Violation(
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
            )
    return violations


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
            _log.debug(
                "TEST005: system %s line cov %.1f%% < %d%%",
                system.id,
                avg,
                cfg.system_line_cov,
            )
            violations.append(
                Violation(
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
            )
    return violations


# frob:ticket T-0148
def _test008_unjoined_root(data: CoverageData) -> tuple[Violation, ...]:
    """TEST008: coverage.xml carried real data but NONE of it joined to a
    known repo path.

    `_coverage.py::_parse_classes` tries every `<sources><source>` root
    Cobertura declared, then a bare-filename fallback, before giving up --
    `data.root_join_ok` is only False when every one of those strategies
    resolved zero `<class>` filenames against a real path. That is a
    silent-death condition (TEST005 would otherwise just report "0
    modules measured" and every consumer of `CoverageData` would quietly
    treat this repo as having no coverage at all) rather than a real
    "nothing to report" state, so it is always an ERROR: this gate ships
    in many sibling repos with different package layouts, and a hardcoded
    or wrong root here must fail loudly, never degrade to a quiet zero.
    """
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
    per-system floor.

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
    if coverage.is_nothing:
        return ()
    data = coverage.danger_some
    exclude_globs = load_exclude_globs(Path(snapshot.root))
    if exclude_globs:
        data = CoverageData(
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
        )
    return (
        *_test008_unjoined_root(data),
        *_test005_symbols(snapshot, data, cfg),
        *_test005_modules(data, cfg),
        *_test005_systems(systems, data, cfg),
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


# frob:doc docs/modules/gates.md#public-api
def test_gate(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    tests: CollectedTests,
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST001..TEST006. Interfaces derived from packages with public symbols
    (see `_test003`'s docstring for the exact alpha semantics). Coverage is
    consumed as recorded evidence, never produced here."""
    violations: list[Violation] = []
    violations.extend(_test001_002(snapshot, tests, cfg))
    violations.extend(_test003(snapshot, tests, cfg))
    violations.extend(_test007_pairs(snapshot, tests, cfg))
    violations.extend(_test004(systems, snapshot, tests))
    violations.extend(_test005(snapshot, systems, coverage, cfg))
    violations.extend(_test006(snapshot))
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


# frob:doc docs/modules/tickets.md#decision-record-t-0162
def tickets_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """TICK001/TICK002: the T-0162 ticket-id collision invariant gate."""
    return _tick001_duplicate_ids(root) + _tick002_draft_on_default(root, queue)


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


def _sys004(design_ids) -> list[Violation]:  # noqa: ANN001
    """SYS004: a `.strata` design file itself failed to parse/elaborate.

    Reported as its own rule, distinct from SYS001, because a load failure
    and a dangling reference are different problems with different fixes
    (fix the design file vs. fix the directive) -- collapsing them would
    misdirect whoever reads the message (reviewer-caught, T-0080 REJECT
    round 1)."""
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
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind not in _SYS_DIRECTIVE_KINDS:
            continue
        if edge.target in valid[edge.kind]:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("SYS001: %s -> %s not in design model", edge.src, edge.target)
        violations.append(
            Violation(
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
        )
    return violations


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
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
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
def _doc003(root: Path, design_ids) -> list[Violation]:  # noqa: ANN001
    """DOC003: a `frob:claims <view>` doc marker whose view is not PROVED
    (zero THREAT001/THREAT002/THREAT003 violations) against the current
    design model is an error naming the failing obligations (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point: "a README claiming
    'protected against the OWASP Top 10' must cite a PROVED exhaustiveness
    result or it fails CI"). DOC002 is already taken (anchor resolution,
    T-0127), hence DOC003 for the claims audit (charter drift noted in
    docs/strata/threat.md).

    Suppressed when any design file failed to load (same posture as
    SYS001): a claim cannot be honestly evaluated against a partially
    loaded model. Runs no doc I/O at all when no `frob:claims` marker
    exists anywhere, so a repo not using the directive pays nothing."""
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
def sys_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """SYS001 (dangling directive), SYS002 (unbound boundary/secret), SYS003
    (undeclared cross-component import, tier-2 conformance), and SYS004 (a
    `.strata` design file failed to parse/elaborate -- suppresses SYS001
    for the whole run since ids are merged across files with no per-file
    provenance).

    Opt-in via a `design/` (or `[strata].design_dir`) directory of `.strata`
    files existing, same posture as `decisions_gate`: a repo not yet using
    strata sees nothing. The `frob.strata` import is deferred until AFTER
    this check (T-0135): `frob.strata` transitively imports `_facts.py`,
    which needs the `strata_core` native extension, so a repo with no
    `design/` dir at all must never pay that import cost -- a standalone
    (`uv tool install frob`, no natives) install must not crash `frob
    check` on every repo, only degrade (T-0134) on repos that actually
    opted into `design/`.
    """
    root = Path(root)
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        _log.debug("sys_gate: no %s/ directory, skipping", design_dir)
        return ()

    from frob.strata import load_design_ids

    design_ids = load_design_ids(root, design_dir)
    violations = (
        *_sys004(design_ids),
        *_sys001(snapshot, design_ids),
        *_sys002(snapshot, design_ids),
        *_sys003(design_ids, root),
        *_doc003(root, design_ids),
    )
    _log.info(
        "sys_gate: %d channel(s)/%d boundary(ies)/%d secret(s) in model, "
        "%d violation(s), %d design load error(s)",
        len(design_ids.channels),
        len(design_ids.boundaries),
        len(design_ids.secrets),
        len(violations),
        len(design_ids.errors),
    )
    return violations


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
    from frob.dup import DUP001, DUP002, DupConfig, core_available, find_clones
    from frob.dup import touched_refs as _touched

    root = Path(root)
    enforce, threshold, region_kernel = _dup_config(root)
    if not enforce:
        _log.debug("dup_gate: [dup].enforce off, skipping")
        return ()
    if not core_available():
        _log.warning("dup_gate: frob-core not installed; DUP rules skipped")
        return ()

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
    violations = (
        *DUP001(report, touched, threshold),
        *DUP002(report, touched, threshold),
    )
    _log.info("dup_gate: %d clone violation(s)", len(violations))
    return tuple(violations)


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
    manifest = manifest_result.danger_ok

    current_version = _current_version(root)
    if current_version is None:
        _log.debug("release_gate: no detectable project version, skipping")
        return ()

    bump, violations = _rel001_version(manifest, snapshot, current_version)
    if bump != 0 and not _changelog_mentions(root, current_version):
        violations.append(
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file="CHANGELOG.md",
                line=0,
                message=(
                    f"REL001: no CHANGELOG.md entry for {current_version}; the "
                    f"public API changed and needs a release note"
                ),
            )
        )
    _log.info("release_gate: bump=%s, %d violation(s)", bump.name, len(violations))
    return tuple(violations)


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
    from frob.fuzz import (
        FUZZ001,
        FUZZ002,
        FUZZ003,
        FuzzEnforce,
        FuzzPolicy,
        load_fuzz_stamp,
        obligations,
        resolve_param_types,
    )

    root = Path(root)
    enforce = _fuzz_enforce(root)
    if enforce == FuzzEnforce.OFF:
        _log.debug("fuzz_gate: [fuzz].enforce=off, skipping")
        return ()

    obs = obligations(snapshot, FuzzPolicy(enforce=enforce))
    param_types = {ob.ref: resolve_param_types(root, ob.ref) for ob in obs}
    stamp = load_fuzz_stamp(root)
    violations = (
        *FUZZ001(snapshot, obs),
        *FUZZ002(obs, param_types),
        *FUZZ003(snapshot, obs, stamp),
    )
    _log.info("fuzz_gate: %d obligation(s), %d violation(s)", len(obs), len(violations))
    return tuple(violations)


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
    violations = [
        Violation(
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
        for orphan in orphans
    ]
    _log.info("doclink: %d obligated, %d orphaned", len(obligated), len(violations))
    return tuple(violations)


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
    """
    root = Path(root)
    violations: list[Violation] = []
    slug_cache: dict[str, Option[set[str]]] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.DOC:
            continue
        origin_file, _, lineno_text = edge.origin.rpartition(":")
        line = int(lineno_text) if lineno_text.isdigit() else 0
        origin_file = origin_file or edge.origin
        target = edge.target
        if "#" not in target:
            violations.append(
                _docanchor_violation(
                    origin_file,
                    line,
                    f"DOC002: frob:doc target {target!r} has no #anchor; "
                    f"use <file>#<slug>",
                )
            )
            continue
        docfile, slug = target.split("#", 1)
        if docfile not in slug_cache:
            slug_cache[docfile] = _doc_anchor_slugs(root / docfile)
        slugs = slug_cache[docfile]
        if slugs.is_nothing:
            violations.append(
                _docanchor_violation(
                    origin_file,
                    line,
                    f"DOC002: frob:doc target file {docfile!r} does not exist",
                )
            )
        elif slug not in slugs.danger_some:
            violations.append(
                _docanchor_violation(
                    origin_file,
                    line,
                    _anchor_mismatch_message(target, docfile, slug, slugs.danger_some),
                )
            )
    _log.info("docanchor: %d violation(s)", len(violations))
    return tuple(violations)


# frob:doc docs/modules/perf.md#integration-points
# frob:ticket T-0021
# frob:ticket T-0203
# frob:waive TEST005 reason="perf_gate 85.7% branch cover, debt T-0160"
def perf_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PERF001..PERF004, run at the policy/gates stage per docs/modules/perf.md's
    Integration points. Parses every source file in `snapshot.file_hashes`
    that carries a registered tree-sitter grammar (`frob.lang.tree_sitter_extensions`,
    the canonical T-0129 extension table -- not a hand-copied duplicate);
    files with no registered grammar are unscannable by design and are
    filtered out before parsing, so they never reach `parse_file` and never
    produce an UnsupportedLanguage skip line (T-0203). A file whose
    extension SHOULD parse but fails still gets a visible skip message.
    Hands the parsed set to `frob.perf.perf_rules` (same posture as
    `frob.policy`'s `_pattern_violations`: gates does the IO, `perf_rules`
    stays pure)."""
    from frob.lang import parse_file, tree_sitter_extensions
    from frob.perf import perf_rules

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

    parsed: list[ParsedFile] = []
    for rel_path in candidate_paths:
        result = parse_file(root / rel_path)
        if result.is_err:
            _log.warning(
                "perf_gate: skipping unparsed %s: %s", rel_path, result.danger_err
            )
            continue
        parsed.append(result.danger_ok)
    violations = perf_rules(snapshot, parsed)
    _log.info(
        "perf_gate: %d file(s) scanned, %d violation(s)", len(parsed), len(violations)
    )
    return violations


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
    }
)


@dataclass(frozen=True)
class _GateInputs:
    """All loaded state the pure gates consume, assembled once by `run_gates`."""

    root: Path
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


def _load_inputs(cfg: GateConfig) -> Result[_GateInputs, GateError]:
    """Load every piece of state the gates need, or the first hard failure."""
    from frob.policy import load_policy

    root = Path(cfg.root)
    build_result: Result[GraphSnapshot, BuildError] = build_graph(
        root, root / _CACHE_REL
    )
    if build_result.is_err:
        _log.error("run_gates: graph build failed: %s", build_result.danger_err)
        return Err(GateError.GraphUnavailable)
    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("run_gates: ticket queue load failed: %s", queue_result.danger_err)
        return Err(GateError.QueueUnavailable)
    lock_result = load_lock(root / "frob.lock")
    if lock_result.is_err:
        _log.error("run_gates: lock load failed: %s", lock_result.danger_err)
        return Err(GateError.ConfigMalformed)
    invariants_result = load_invariants(root)
    if invariants_result.is_err:
        _log.error(
            "run_gates: invariants load failed: %s", invariants_result.danger_err
        )
        return Err(GateError.ConfigMalformed)
    policy_result = load_policy(root)
    if policy_result.is_err:
        _log.error("run_gates: policy load failed: %s", policy_result.danger_err)
        return Err(GateError.ConfigMalformed)

    snapshot = build_result.danger_ok
    queue = queue_result.danger_ok
    rules = policy_result.danger_ok
    coverage_result = load_coverage(root, snapshot)
    coverage: Option[CoverageData] = (
        Some(coverage_result.danger_ok) if coverage_result.is_ok else Nothing()
    )
    test_policy, systems = _load_test_config(root)
    ticket, sweep = _resolve_ticket(root, cfg, queue)
    return Ok(
        _GateInputs(
            root=root,
            cfg=cfg,
            snapshot=snapshot,
            queue=queue,
            lock=lock_result.danger_ok,
            diff=_load_diff(root, cfg.base),
            tests=_load_tests(root),
            invariants=invariants_result.danger_ok,
            rules=tuple(rules),
            rule_ids=frozenset(r.id for r in rules),
            coverage=coverage,
            test_policy=test_policy,
            systems=systems,
            ticket=ticket,
            sweep=sweep,
        )
    )


def _build_jobs(
    selected: frozenset[str], st: _GateInputs
) -> tuple[dict[str, Callable[[], tuple[Violation, ...]]], list[str]]:
    """Map each selected gate name to a zero-arg job over the loaded state."""
    from frob.policy import policy_gate

    jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {}
    skipped: list[str] = []
    if "drift" in selected:
        jobs["drift"] = lambda: drift_gate(st.snapshot, st.lock)
    if "coverage" in selected:
        jobs["coverage"] = lambda: coverage_gate(
            st.snapshot, st.queue, st.diff, st.tests
        )
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
    if "invariant" in selected:
        jobs["invariant"] = lambda: invariant_gate(
            st.invariants, st.snapshot, st.tests, st.rule_ids
        )
    if "test" in selected:
        jobs["test"] = lambda: test_gate(
            st.snapshot, st.systems, st.coverage, st.tests, st.test_policy
        )
    if "policy" in selected:
        jobs["policy"] = lambda: policy_gate(st.rules, st.snapshot, st.diff)
    if "doclink" in selected:
        jobs["doclink"] = lambda: doclink_gate(st.root, st.snapshot)
    if "docanchor" in selected:
        jobs["docanchor"] = lambda: docanchor_gate(st.root, st.snapshot)
    if "perf" in selected:
        jobs["perf"] = lambda: perf_gate(st.root, st.snapshot)
    if "fuzz" in selected:
        jobs["fuzz"] = lambda: fuzz_gate(st.root, st.snapshot)
    if "release" in selected:
        jobs["release"] = lambda: release_gate(st.root, st.snapshot)
    if "clones" in selected:
        jobs["clones"] = lambda: dup_gate(st.root, st.snapshot, st.diff)
    if "decisions" in selected:
        jobs["decisions"] = lambda: decisions_gate(st.root, st.snapshot)
    if "sys" in selected:
        jobs["sys"] = lambda: sys_gate(st.root, st.snapshot)
    if "secrets" in selected:
        jobs["secrets"] = lambda: secrets_gate(st.root)
    if "tickets" in selected:
        jobs["tickets"] = lambda: tickets_gate(st.root, st.queue)
    return jobs, skipped


def _run_jobs(
    jobs: dict[str, Callable[[], tuple[Violation, ...]]],
) -> tuple[list[Violation], dict[str, int], dict[str, float]]:
    """Run the gate jobs in parallel; return merged violations, counts, timing."""
    from concurrent.futures import ThreadPoolExecutor

    counts: dict[str, int] = {}
    timing: dict[str, float] = {}
    violations: list[Violation] = []
    if not jobs:
        return violations, counts, timing
    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {}
        for name, job in jobs.items():
            futures[pool.submit(job)] = (name, time.monotonic())
        for future in futures:
            name, job_start = futures[future]
            result = future.result()
            timing[name] = time.monotonic() - job_start
            counts[name] = len(result)
            violations.extend(result)
            _log.info(
                "run_gates: %s -> %d violation(s) in %.3fs",
                name,
                len(result),
                timing[name],
            )
    return violations, counts, timing


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

    jobs, skipped = _build_jobs(selected, st)
    all_violations: list[Violation] = [
        *_waive001_violations(st.snapshot),
        *_waive002_violations(st.snapshot, st.rule_ids),
    ]
    job_violations, counts, timing = _run_jobs(jobs)
    counts["waive"] = len(all_violations)
    all_violations.extend(job_violations)

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
    return Ok(GateReport(violations=kept, waived=waived, stats=stats))


__all__ = [
    "CoverageData",
    "CoverageError",
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
    "coverage_gate",
    "delta_violations",
    "drift_gate",
    "invariant_gate",
    "is_baseline_stale",
    "load_baseline",
    "load_coverage",
    "load_invariants",
    "decisions_gate",
    "doclink_gate",
    "docanchor_gate",
    "dup_gate",
    "fuzz_gate",
    "perf_gate",
    "release_gate",
    "prework_gate",
    "record_prework",
    "run_gates",
    "scope_digest",
    "scope_gate",
    "secrets_gate",
    "stamp_baseline",
    "stamp_coverage",
    "sys_gate",
    "test_gate",
    "violation_fingerprint",
]
