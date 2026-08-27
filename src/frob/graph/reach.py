"""T-3046: "does this bound evidence actually reach the code it certifies"
(docs/modules/graph.md#evidence-reach-t-3046).

M6 finding: T-3005 and T-3007 both landed with evidence bound to
`tests/unit/strata/test_parse.py` node ids -- parser tests that never
touch the Rust graph code either ticket added. Both passed `frob`'s D-02
`evidence_covers_scope` check because that check has TWO routes, and one
of them is a self-declaration with no verification at all: an evidence id
whose OWN file is directly named in `ticket.scope`/`ticket.evidence_scope`
counts as covering, with no check that anything in that file's tests
actually exercises the ticket's changed code. Declaring
`evidence_scope: [tests/unit/strata/test_parse.py]` is exactly as easy
whether or not that file's tests touch the ticket's real work.

THE RULE below closes that gap the same way `frob.ci_validity` (T-2985)
closes the analogous "is this CI result still evidence" question, and
using the SAME machinery -- no new traversal engine:

  - `REACHES` -- the bound test's execution can reach a symbol the
    ticket's scope names, via any of: (a) the test's own call TOKENS
    (`RawSymbol.body_tokens`, a real per-call-site token scan, PUBLIC or
    private -- the direct-call case, and the dominant real pattern: a
    test importing and calling the public function under test) name a
    scoped symbol's short name; (b) the test's own PRIVATE-callee
    closure (`frob.graph.callgraph.build_call_graph` + `closure`)
    includes a scoped symbol (the transitive case (a) cannot see); or
    (c) the test's own file IS a scoped file (co-located test, the one
    case self-declaration is actually sound).
  - `DOES_NOT_REACH` -- the closure was computed successfully and
    contains no scoped symbol, and the test's file is not itself scoped.
    This is the laundering shape the M6 finding names.
  - `UNKNOWN` -- reachability could not be determined at all: the test
    symbol does not resolve in the graph, OR the ticket's scope names no
    Python file the call graph can represent (a Rust/C++/TS-only change
    -- exactly T-3005/T-3007's shape). `UNKNOWN` is never rendered as a
    pass, matching `frob.ci_validity.Validity.UNKNOWN` and `frob.verify`'s
    stale-baseline refusal doctrine (docs/modules/ci_validity.md).

DECISION for the Rust/native-only case (the situation T-3005/T-3007 were
actually in): today's kernel has no cross-language call graph, so a
pytest node id binding for a scope containing only non-Python files is
`UNKNOWN` by construction, ALWAYS -- never `REACHES`, no matter which
pytest id is cited. "There is no Python test that reaches this" is a
legitimate answer (the module's own crate tests are the real evidence,
per T-3007's Done report), but it must be recorded as an explicit
`UNKNOWN`/waiver, not silently accepted as a pass because an unrelated
pytest id happened to be green. Wiring this classifier into a live
`frob check` gate stage is a follow-up ticket (see
docs/modules/graph.md#evidence-reach-t-3046 for its id and why it is not
wired yet) -- `scripts/measure_evidence_reach.py` is the standalone
repo-wide measurement in the meantime.

Built entirely on:
  - `frob.graph.callgraph.build_call_graph`/`closure` -- the SAME private-
    callee call-graph resolution `frob.graph.scope_private_helper_gaps`
    already uses for a different scope question (T-0998).
  - `frob.tickets._models.scope_matches` -- THE one scope-membership
    check every other scope-consulting site uses (T-0241); no second
    glob-matching copy here.

This module never mutates anything and never talks to git directly --
callers pass in an already-built `GraphSnapshot` and an already-resolved
file list, matching `frob.graph.affects.affects`'s own pure posture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from frob.excludes import iter_files
from frob.graph._models import GraphSnapshot
from frob.graph.callgraph import build_call_graph, closure, is_symref
from frob.lang import parse_file
from frob.logging import get_logger
from frob.tickets._models import scope_matches

_log = get_logger(__name__)

# Extensions the call graph can represent at all today (T-0998's own
# `build_call_graph` operates over `frob.lang`'s supported grammars).
# Anything scoped outside these is, for THIS check, structurally
# unrepresentable -- never silently treated as "no code to reach".
_CALLGRAPH_EXTENSIONS = (".py",)

# Other-LANGUAGE source extensions that make a scope "native/non-Python"
# for this check's UNKNOWN decision (T-3046's own decision for the
# Rust-only case). Deliberately narrow to real CODE extensions -- a scope
# entry that is a doc/config/data file (`.md`, `.toml`, `.json`, `.yaml`,
# ...) accompanying an ordinary Python change must NOT trip this (every
# ticket in this repo scopes at least one doc file; treating that as
# "native-only" would make this check UNKNOWN almost everywhere and say
# nothing).
_OTHER_LANGUAGE_CODE_EXTENSIONS = (
    ".rs",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".rb",
)


# frob:doc docs/modules/graph.md#evidence-reach-t-3046
# frob:tests tests/test_graph_reach.py::TestClassifyEvidenceReach.test_reaches_via_call_graph_closure  # noqa: E501
class EvidenceReach:
    """The three classification values `classify_evidence_reach` can
    return. Plain string constants (not a `StrEnum`), matching
    `frob.ci_validity.Validity`'s own reasoning: byte-stable `--json`
    rendering as a bare string field, no enum serialization decision."""

    REACHES = "reaches"
    DOES_NOT_REACH = "does_not_reach"
    UNKNOWN = "unknown"


# frob:doc docs/modules/graph.md#evidence-reach-t-3046
# frob:tests tests/test_graph_reach.py::TestClassifyEvidenceReach.test_reaches_via_call_graph_closure  # noqa: E501
class ReachResult(BaseModel):
    """One evidence id's classification against one ticket's scope:
    `status` is one of `EvidenceReach`'s three values, `reason` is a
    short human-readable justification -- never left implicit, matching
    `frob.ci_validity.TestValidity`'s own "no bare verdict" discipline."""

    model_config = ConfigDict(frozen=True)

    evidence: str
    status: str
    reason: str


# frob:waive DUP001 reason="duplicated locally from \
# frob.ci_validity._node_id_to_symref per that module's OWN established T-2018 \
# precedent -- a small, stable helper is copied once rather than reached through a \
# private cross-module import; see this function's own docstring"
def _node_id_to_symref(node_id: str) -> str:
    """`file::Class::method` (pytest node id shape) to `file::Class.method`
    (canonical dotted symref shape) -- duplicated locally from
    `frob.ci_validity._node_id_to_symref` per that module's own
    established T-2018 precedent (a small, stable helper is copied once
    rather than reached through a private cross-module import)."""
    if "::" not in node_id:
        return node_id
    path, rest = node_id.split("::", 1)
    qualname = rest.replace("::", ".")
    return f"{path}::{qualname}"


def _scoped_python_files(root: Path, scope: Sequence[str]) -> tuple[str, ...]:
    """Every `.py` file under `root` that `scope_matches(path, scope)` --
    the ticket's scope restricted to files the call graph can represent
    at all. `frob.excludes.iter_files` (T-0471's shared pruned-walk/`git
    ls-files` primitive) does the actual traversal, so this never repeats
    the raw-`rglob` mistake WALK001 exists to catch."""
    matched: list[str] = []
    for path in sorted(iter_files(root, suffix=".py")):
        rel = path.relative_to(root).as_posix()
        if scope_matches(rel, scope):
            matched.append(rel)
    return tuple(matched)


def _scope_has_non_python_member(root: Path, scope: Sequence[str]) -> bool:
    """True when `scope` names at least one real file in another
    language's SOURCE extension (`_OTHER_LANGUAGE_CODE_EXTENSIONS`) --
    the signal used to decide whether a scope is "Rust/native-only" for
    this check's purposes. Deliberately does NOT trigger on doc/config/
    data files that merely accompany an ordinary Python change (see
    `_OTHER_LANGUAGE_CODE_EXTENSIONS`'s own docstring). A scope entry
    that matches no file on disk (a stale glob) is not counted either
    way. Uses `frob.excludes.iter_files` (module docstring, T-0471), not
    a raw `rglob`."""
    for path in sorted(iter_files(root)):
        rel = path.relative_to(root).as_posix()
        if scope_matches(rel, scope) and path.suffix in _OTHER_LANGUAGE_CODE_EXTENSIONS:
            return True
    return False


def _direct_called_short_names(root: Path, file: str, qualname: str) -> frozenset[str]:
    """The identifier tokens `qualname`'s own body in `file` calls (a
    real per-call-site token scan over the parsed AST, PUBLIC or private
    callees alike -- unlike `build_call_graph`, which only ever records
    an edge to a PRIVATE callee). This is what lets a test that directly
    imports and calls the public function under test count as reaching
    it, without needing a transitive private-callee closure at all --
    the dominant real pattern `build_call_graph` alone structurally
    cannot see (module docstring). Returns an empty set (never raises)
    on a parse failure or an unresolved qualname -- callers treat that
    as "no direct hit found", falling through to the closure route."""
    result = parse_file(root / file, expect_heterogeneous=True)
    if result.is_err:
        return frozenset()
    for sym in result.danger_ok.symbols:
        if sym.qualname != qualname:
            continue
        names: set[str] = set()
        tokens = sym.body_tokens
        for i in range(len(tokens) - 1):
            if tokens[i + 1] == "(" and tokens[i].isidentifier():
                names.add(tokens[i])
        return frozenset(names)
    return frozenset()


def _is_test_shaped(path: str) -> bool:
    """Heuristic used ONLY to keep a test's own file from counting as
    "reached production code" when computing `scoped_symbols`: a bare
    `tests/` prefix or a `test_*.py`/`*_test.py` basename. This is what
    stops the exact M6 hole from reappearing inside the call-graph route
    too -- without it, a scope entry that happens to include the cited
    test's OWN file (see `evidence_scope` below) would let that test's
    calls to its own private helpers count as "reaching scope", which is
    exactly as vacuous as the bare file-membership shortcut this module
    replaces."""
    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") or name.startswith("test_") or name.endswith(
        "_test.py"
    )


# frob:doc docs/modules/graph.md#evidence-reach-t-3046
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_reaches_via_call_graph_clos\
# ure
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_reaches_via_co_located_test\
# _file
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_does_not_reach_when_closure\
# _misses_scope
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_unknown_when_test_symbol_un\
# resolved
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_unknown_when_scope_is_nativ\
# e_only
# frob:tests \
# tests/test_graph_reach.py::TestClassifyEvidenceReach.test_evidence_scope_alone_does_n\
# ot_launder_reach
# frob:ticket T-3046
def classify_evidence_reach(
    root: Path,
    snapshot: GraphSnapshot,
    scope: Sequence[str],
    evidence: str,
    *,
    evidence_scope: Sequence[str] = (),
) -> ReachResult:
    """Classify one `evidence` id (a pytest node id) against a ticket's
    real declared `scope` (module docstring's three-way rule).

    `scope` and `evidence_scope` are DELIBERATELY not treated the same.
    `scope` is a write-lease claim -- the ticket asserts it is actually
    changing that file, which is the same signal `frob.gates.
    evidence_covers_scope`'s route 2 already trusts for a co-located
    test (`scope: [src/foo.py, tests/test_foo.py]`). `evidence_scope`
    (T-1944) is a bare, unverified POINTER at a pre-existing test file
    with NO lease claim -- this is the exact field T-3005/T-3007 used to
    self-declare `tests/unit/strata/test_parse.py` as "covering" a
    strata-core Rust change it never touches (the M6 finding this module
    exists to close). So: a test whose OWN file is directly in `scope`
    is `REACHES` outright (route 2's existing trust, unchanged); a test
    whose file is only in `evidence_scope` gets NO such shortcut -- it
    must prove reach the same way anything else does, through the real
    call graph, with its own file's symbols excluded from what counts as
    "reached" (`_is_test_shaped`) so it cannot pass by calling its own
    neighbors.

    `evidence_scope` files still widen the file set this function
    resolves symbols and builds the call graph over (a test needs its
    own file parsed to resolve `test_ref` in `snapshot.symbols` at all),
    they just never count as a scope MEMBER to reach into.

    `cmd:`-shaped evidence and any non-`::`-bearing bare path are out of
    this function's scope (the caller is expected to only pass pytest
    node ids here); passing one resolves as `UNKNOWN` rather than
    raising, since "not a pytest id" is itself something this check
    cannot determine reach for.
    """
    if "::" not in evidence:
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.UNKNOWN,
            reason="not a pytest node id (no '::') -- reach cannot be classified",
        )

    test_file = evidence.split("::", 1)[0]
    if scope_matches(test_file, scope):
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.REACHES,
            reason=f"{test_file} is itself a scoped file (co-located test)",
        )

    if _scope_has_non_python_member(root, scope):
        _log.info(
            "classify_evidence_reach: %r: scope has a non-Python member -- "
            "UNKNOWN (no cross-language call graph)",
            evidence,
        )
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.UNKNOWN,
            reason=(
                "ticket scope contains a non-Python file; frob has no "
                "cross-language call graph, so a pytest binding cannot "
                "prove reach into it -- bind the native test suite's own "
                "evidence explicitly (T-3046 decision) instead of relying "
                "on this check"
            ),
        )

    scoped_files = _scoped_python_files(root, scope)
    if not scoped_files:
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.UNKNOWN,
            reason="ticket scope matches no file on disk -- cannot classify reach",
        )

    test_ref = _node_id_to_symref(evidence)
    if test_ref not in snapshot.symbols:
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.UNKNOWN,
            reason=f"test symbol {test_ref!r} not resolvable in the graph snapshot",
        )

    return _classify_via_tokens_and_closure(
        root, snapshot, evidence, evidence_scope, scoped_files, test_file, test_ref
    )


def _classify_via_tokens_and_closure(
    root: Path,
    snapshot: GraphSnapshot,
    evidence: str,
    evidence_scope: Sequence[str],
    scoped_files: tuple[str, ...],
    test_file: str,
    test_ref: str,
) -> ReachResult:
    """The direct-call-token and call-graph-closure half of
    `classify_evidence_reach` (extracted per ARCH001): once `scope` has a
    representable Python file and `test_ref` resolves, try the direct
    call-token route first (cheap, catches the dominant real pattern),
    then the transitive private-callee closure, then `DOES_NOT_REACH`."""
    scoped_symbols = {
        record.symref
        for record in snapshot.symbols.values()
        if record.id.path in scoped_files and not _is_test_shaped(record.id.path)
    }

    test_qualname = test_ref.split("::", 1)[-1]
    scoped_short_names = {
        s.rsplit("::", 1)[-1].rsplit(".", 1)[-1] for s in scoped_symbols
    }
    direct_called = _direct_called_short_names(root, test_file, test_qualname)
    direct_hit = direct_called & scoped_short_names
    if direct_hit:
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.REACHES,
            reason=(
                f"{test_ref} directly calls {sorted(direct_hit)[0]!r}, a "
                "scoped symbol's short name"
            ),
        )

    evidence_scope_files = _scoped_python_files(root, tuple(evidence_scope))
    graph_files = tuple(sorted({*scoped_files, *evidence_scope_files, test_file}))
    call_graph = build_call_graph(root, graph_files)
    reachable = {c for c in closure(call_graph, test_ref) if is_symref(c)}

    hit = reachable & scoped_symbols
    if hit:
        return ReachResult(
            evidence=evidence,
            status=EvidenceReach.REACHES,
            reason=f"{test_ref}'s call-graph closure reaches {sorted(hit)[0]}",
        )

    return ReachResult(
        evidence=evidence,
        status=EvidenceReach.DOES_NOT_REACH,
        reason=(
            f"{test_ref}'s call-graph closure ({len(reachable)} private "
            "callee(s)) contains no symbol under the ticket's scope -- "
            "this evidence id does not exercise the changed code (an "
            "evidence_scope-only file-name match does not count as "
            "reach, see T-3046)"
        ),
    )


__all__ = [
    "EvidenceReach",
    "ReachResult",
    "classify_evidence_reach",
]
