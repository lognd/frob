"""DEAD001: an unreferenced private symbol is dead code
(docs/modules/gates.md#rule-catalog, T-0422).

Motivating case (T-0418): `_arch_violations_from_suggestions` was written
to fix a real bug but never wired -- zero callers, dead code, and no gate
flagged it. This is the SYMBOL-level analog of the anti-orphan FILE gate
(REF001/T-0396, `frob.gates._refs`): a file with no inbound reference is
an orphan file; a private (leading-underscore, `SymbolRecord.public is
False`) function/class/method with no inbound reference is an orphan
symbol.

Two independent "wired" signals, either one exempts a symbol:

1. REFERENCED: the symbol's symref appears in its own package's
   intra-package reference graph (`frob.graph.callgraph.
   build_reference_graph`, T-0422's broadened sibling of the shared
   `build_call_graph` substrate `frob.dup` and the COV006 reachability
   check already use -- no bespoke third parser here, and no whole-repo
   re-walk: exactly the bounded, per-package file set `build_call_graph`
   was designed for, one package at a time). Broadened, not just a call
   token (`name(...)`), to also catch a dispatch-table/registry entry
   (`COMMANDS = {"new": _new}`) or a decorator target -- `build_call_
   graph` alone measured a large false-positive rate on this repo's own
   `app/*_runner.py` dispatch tables (see this module's Done report).
2. DECLARED: an existing graph edge (`GraphSnapshot.edges`, already
   computed by `frob.graph.build_graph` in the SAME pass that produced
   `snapshot.symbols` -- no second traversal for this half) of kind
   TESTS, DESCRIBES, or INVARIANT targets the symbol directly. A bare
   `frob:ticket` tag does NOT count (every symbol in this repo carries
   one; treating it as "wired" would make this gate fire on nothing).

False-positive guards (T-0422's acceptance criteria): dunder methods
(`__init__`, `__post_init__`, ...), pytest `test_*` functions/`Test*`
classes, and anything a caller waives with `frob:waive DEAD001
reason="..."` (the standard mechanism every other advisory-tier gate in
this repo already uses for a case this best-effort token scan cannot
see -- e.g. a handler reached only via `getattr(obj, "_name")` string
dispatch, which never appears as a bare identifier token at all).

WARN-only (advisory-but-tracked, matching REF/PERF/FUZZ's posture) --
never blocks a build on its own, but every finding must eventually be
fixed (wire it or delete it) or waived with an honest reason.

Python (`.py`) files ONLY in this pass -- see `dead_symbol_gate`'s
docstring for why Rust/TypeScript/C are excluded (a real soundness gap
in the shared `frob.graph.callgraph` substrate's privacy detection, not
a scope choice of convenience).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path, PurePosixPath

from frob.gates._models import Severity, Violation
from frob.graph import EdgeKind, GraphSnapshot, build_reference_graph
from frob.lang import SymbolKind, supported_extensions
from frob.logging import get_logger

_log = get_logger(__name__)

# Kinds this gate reasons about -- CONST/TYPE are data declarations, not
# "wired by being called", and would be pure noise under a call-graph
# reachability check.
_CALLABLE_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CLASS})

# Edge kinds -- other than DESCRIBES, handled separately for its reversed
# src/target direction -- that count as an explicit DECLARED reference to
# a symbol via `Edge.src` (the code symbol the directive lives above).
# Deliberately excludes TICKET (near-universal in this repo, so treating
# it as "wired" would silence this gate entirely) and WAIVE/TODO/DEBT
# (bookkeeping about the symbol, not evidence something else consumes it).
_DECLARED_REFERENCE_KINDS = frozenset({"tests", "invariant"})


def _is_dunder(qualname: str) -> bool:
    """True for a `__name__`-shaped final qualname component (`__init__`,
    `Foo.__post_init__`, ...) -- never flagged, these are protocol hooks
    the language runtime calls, not something any tracked caller invokes
    by name."""
    short = qualname.rsplit(".", 1)[-1]
    return short.startswith("__") and short.endswith("__")


def _is_test_symbol(qualname: str) -> bool:
    """True for a `test_*`/`Test*`-named function/method/class (leading
    underscores stripped first, so a PRIVATE test helper like
    `_test_setup` still counts) -- called by the test RUNNER via naming
    convention or by pytest fixture/setup discovery, never by another
    tracked symbol's call token, so a call-graph reachability check would
    otherwise flag every test as dead (same class of false positive
    `frob.gates._refs`'s file-level gate already exempts)."""
    parts = qualname.split(".")
    return any(p.lstrip("_").startswith(("test_", "Test")) for p in parts)


# frob:ticket T-0422
def _package_files(root: Path, rel_path: str) -> tuple[str, ...]:
    """Every language-supported file beside `rel_path` (same directory),
    repo-root-relative POSIX -- the bounded file set `build_reference_graph`
    resolves intra-package private calls over, one package at a time."""
    directory = (root / rel_path).parent
    if not directory.is_dir():
        return (rel_path,)
    exts = supported_extensions()
    found = tuple(
        sorted(
            (directory / name).relative_to(root).as_posix()
            for name in (p.name for p in directory.iterdir())
            if (directory / name).is_file()
            and (directory / name).suffix.lower() in exts
        )
    )
    return found or (rel_path,)


def _declared_referenced_symrefs(snapshot: GraphSnapshot) -> frozenset[str]:
    """Every symref an existing TESTS/DESCRIBES/INVARIANT edge already
    binds to a code symbol (`_DECLARED_REFERENCE_KINDS`) -- pure lookup
    over `snapshot.edges`, already computed by `build_graph`'s single
    pass, no re-derivation.

    Direction differs by kind: a `frob:tests`/`frob:invariant` comment
    lives ABOVE the code symbol it binds (`Edge.src` is that code
    symbol's own symref, `Edge.target` is the test id / invariant id); a
    markdown `frob:describes` anchor lives in the DOC file instead
    (`Edge.src` is the doc anchor, `Edge.target` is the code symbol) --
    so TESTS/INVARIANT contribute `edge.src` here, DESCRIBES contributes
    `edge.target`."""
    referenced: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind is EdgeKind.DESCRIBES:
            referenced.add(edge.target.split("#", 1)[0])
        elif edge.kind.value in _DECLARED_REFERENCE_KINDS:
            referenced.add(edge.src.split("#", 1)[0])
    return frozenset(referenced)


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0422
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_unwired_private_function_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_called_private_helper_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_dunder_method_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_test_function_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_tests_edge_target_is_not_flagged  # noqa: E501
# frob:enforces CHK-GATE-DEAD001
# frob:waive ARCH001 reason="the per-package reference-graph cache (called_by_package) is built lazily inside the loop and keyed by the record being examined; splitting the per-record body into a helper would require passing the mutable cache dict and root/package derivation across a new boundary for no reduction in branching, the same shape already accepted for this module's sibling gates"  # noqa: E501
def dead_symbol_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEAD001: a private (leading-underscore) function/class/method with
    no call-graph caller and no TESTS/DESCRIBES/INVARIANT edge is
    unreferenced -- written but never wired, or genuinely dead. Every
    package's own `build_reference_graph` result is built once and reused for
    every private symbol declared in that package (never rebuilt per
    symbol).

    Python files ONLY (`.py`): `build_reference_graph`'s callee-privacy check
    (`callgraph._short_name_index`) hardcodes the leading-underscore
    convention `SymbolRecord.public` uses for Python
    (`frob.lang._walk_python`) -- but Rust (`pub`), TypeScript
    (`export`), and C (`static`) each compute `public` from a completely
    different marker, one the call graph never consults. Running this
    check against those languages measured a ~100% false-positive rate
    on this repo's own `frob-core`/`strata-core` Rust sources (every
    `Parser.advance`-style heavily-called method came back "uncalled"
    because the call graph never even attempts to resolve a callee whose
    short name lacks a leading underscore) -- a soundness gap in the
    shared substrate, not something this gate should paper over with a
    per-language guess. See this ticket's Done report for the filed
    follow-up."""
    referenced = _declared_referenced_symrefs(snapshot)
    called_by_package: dict[str, frozenset[str]] = {}
    violations: list[Violation] = []

    for record in snapshot.symbols.values():
        if record.public or record.kind not in _CALLABLE_KINDS:
            continue
        if not record.id.path.endswith(".py"):
            continue
        qualname = record.id.qualname
        if _is_dunder(qualname) or _is_test_symbol(qualname):
            continue
        symref = record.symref
        if symref in referenced:
            continue
        package = str(PurePosixPath(record.id.path).parent)
        called = called_by_package.get(package)
        if called is None:
            files = _package_files(root, record.id.path)
            graph = build_reference_graph(root, files)
            called = frozenset(
                callee for callees in graph.calls.values() for callee in callees
            )
            called_by_package[package] = called
        if symref in called:
            continue
        violations.append(
            Violation(
                rule="DEAD001",
                severity=Severity.WARN,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"DEAD001: {symref} is a private symbol with no call-graph "
                    "caller and no frob:tests/frob:describes/frob:invariant edge "
                    "-- wire it, delete it, or "
                    'frob:waive DEAD001 reason="..." if it is reached only '
                    "dynamically"
                ),
            )
        )
    _log.info(
        "dead_symbol_gate: %d package(s) scanned, %d violation(s)",
        len(called_by_package),
        len(violations),
    )
    return tuple(violations)
