"""PROTO001: a `frob:requires`/`frob:transition`-tagged function's protocol
summary is poisoned by an unresolved callee (docs/modules/gates.md#proto001-t-0813).

T-0813, the production wiring the T-0809 reviewer's condition (a) asked
for: `frob.graph.summary.compute_protocol_summaries`'s `UNRESOLVED_CALLEE`
poisoning channel (T-0745, NO-FAIL-SILENT mandate) had no real repo-scan
consumer -- `mark_unresolved=True` was opt-in and production-dead, tested
only against hand-fabricated fixtures. T-0814 hardened every closure
consumer of `frob.graph.callgraph.build_call_graph`'s output against the
non-symref `UNRESOLVED_CALLEE` sentinel; this gate is the first real
caller that turns `mark_unresolved=True` on and lets the poisoning
propagate all the way to a `frob check` finding.

Scope, deliberately narrow: only a symbol that ITSELF carries a
`frob:requires`/`frob:transition` directive (i.e. explicitly opted into
the T-0744 protocol DSL) is ever reported here -- not every private
helper with an unresolved call, which would just be `DEAD001`/general
call-graph noise with no protocol stake in it. `compute_protocol_summaries`
still analyzes every function transitively reachable from those tagged
entrypoints (poisoning propagates through plain helpers too, T-0745's
NO-FAIL-SILENT contract) -- this gate only DECIDES WHICH summaries are
worth reporting on, it does not narrow what the engine itself computes.

WARN-only (advisory-but-tracked, matching DEAD001/REF/PERF/FUZZ's posture)
-- `build_call_graph`'s callee resolution is best-effort, name-based, no
scope/overload disambiguation (same caveat every other consumer of this
substrate carries), so a false positive here is possible; waivable with
`frob:waive PROTO001 reason="..."` like every other advisory rule.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from frob.gates._models import Severity, Violation
from frob.graph import EdgeKind, GraphSnapshot
from frob.graph.callgraph import build_call_graph
from frob.graph.dsl import parse_directives
from frob.graph.summary import compute_protocol_summaries
from frob.logging import get_logger

_log = get_logger(__name__)

# Directive kinds that mark a symbol as an explicit T-0744 protocol
# participant -- the only symbols this gate ever reports a poisoned
# summary for (see module docstring's scope note).
_PROTOCOL_TAG_KINDS = frozenset({EdgeKind.REQUIRES, EdgeKind.TRANSITION})


# frob:ticket T-0813
def _package_files(root: Path, rel_path: str) -> tuple[str, ...]:
    """Every language-supported file beside `rel_path` (same directory),
    repo-root-relative POSIX -- the bounded file set `build_call_graph`
    resolves intra-package private calls over, one package at a time.
    Deliberately duplicated from `frob.gates._dead_symbols`'s identical
    helper rather than imported cross-module: both are private
    (leading-underscore) symbols of a sibling gate module with no shared
    public home yet, and this gate additionally needs `.py`-only files
    filtered out of any non-Python candidate BEFORE `build_call_graph`
    ever sees them (see `_protocol_tagged_symrefs_by_package`'s own
    Python-only note) -- a genuinely different filter than
    `_dead_symbols`'s all-language variant, not a copy-paste of the exact
    same contract."""
    from frob.lang import supported_extensions

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


def _package_edges(root: Path, files: tuple[str, ...]) -> tuple:
    """Every `frob:` directive `Edge` parsed from `files` (skipping any
    that fails to parse, logged) -- the `compute_protocol_summaries`
    `edges` argument, built fresh per package since `frob.graph.dsl` has
    no repo-wide cache of its own."""
    from frob.lang import parse_file

    edges: list = []
    for rel_path in files:
        if not rel_path.endswith(".py"):
            continue
        result = parse_file(root / rel_path)
        if result.is_err:
            _log.warning(
                "protocol_summary_gate: skipping unparsed %s: %s",
                rel_path,
                result.danger_err,
            )
            continue
        file_edges, _malformed = parse_directives(result.danger_ok)
        edges.extend(file_edges)
    return tuple(edges)


# frob:doc docs/modules/gates.md#proto001-t-0813
# frob:enforces CHK-GATE-PROTO001
# frob:ticket T-0813
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_unresolved_callee_poisons_a_protocol_tagged_symbol  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_clean_protocol_tagged_symbol_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_untagged_symbol_with_unresolved_call_is_not_flagged  # noqa: E501
def protocol_summary_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PROTO001: the real `mark_unresolved=True` production entrypoint into
    `frob.graph.summary.compute_protocol_summaries` (T-0813) -- every
    symbol carrying a `frob:requires`/`frob:transition` directive gets a
    real, repo-scanned protocol summary; one whose summary comes back
    `poisoned` (an unresolved callee somewhere in its transitive call
    closure) is reported.

    Python files ONLY (`.py`): `build_call_graph`'s callee-privacy check
    hardcodes the leading-underscore convention Python's `SymbolRecord.
    public` uses -- the same Rust/TypeScript/C soundness gap `DEAD001`
    (`frob.gates._dead_symbols.dead_symbol_gate`) already disclosed and
    scoped around, not a new gap this gate introduces.

    Grouped and cached per package (same directory), mirroring `DEAD001`'s
    posture -- `build_call_graph`/`_package_edges` run at most once per
    package regardless of how many protocol-tagged symbols it contains."""
    tagged_by_package: dict[str, list[str]] = {}
    for edge in snapshot.edges:
        if edge.kind not in _PROTOCOL_TAG_KINDS:
            continue
        symref = edge.src
        path = symref.split("::", 1)[0]
        if not path.endswith(".py"):
            continue
        package = str(PurePosixPath(path).parent)
        tagged_by_package.setdefault(package, []).append(symref)

    violations: list[Violation] = []
    packages_scanned = 0
    for package, symrefs in tagged_by_package.items():
        entrypoints = sorted(set(symrefs))
        sample_symref = entrypoints[0]
        sample_path = sample_symref.split("::", 1)[0]
        files = _package_files(root, sample_path)
        callgraph = build_call_graph(root, files, mark_unresolved=True)
        edges = _package_edges(root, files)
        result = compute_protocol_summaries(callgraph, edges, entrypoints)
        packages_scanned += 1
        for symref in entrypoints:
            summary = result.summaries.get(symref)
            if summary is None or not summary.poisoned:
                continue
            record = snapshot.symbols.get(symref)
            file = symref.split("::", 1)[0]
            line = record.span[0] if record is not None else 0
            violations.append(
                Violation(
                    rule="PROTO001",
                    severity=Severity.WARN,
                    file=file,
                    line=line,
                    message=(
                        f"PROTO001: {symref}'s protocol summary is poisoned "
                        f"({summary.poison_reason}) -- an unresolved callee "
                        "somewhere in its transitive call closure makes its "
                        "requires/transitions untrustworthy; fix the call, "
                        'or frob:waive PROTO001 reason="..." if the callee '
                        "resolves dynamically"
                    ),
                )
            )
    _log.info(
        "protocol_summary_gate: %d package(s) scanned, %d protocol-tagged "
        "symbol(s), %d violation(s)",
        packages_scanned,
        sum(len(v) for v in tagged_by_package.values()),
        len(violations),
    )
    return tuple(violations)
