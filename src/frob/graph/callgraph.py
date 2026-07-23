"""Interprocedural call-graph substrate (docs/modules/graph.md#call-graph).

Shared facility -- built once so `frob.dup` (helper-inlining triage, T-0288)
and future arch work (recursion detection, T-0290) both consume the same
call-resolution logic rather than re-deriving it. Resolves calls to PRIVATE
(leading-underscore) or otherwise module-local helpers within a single file
or a single package (same directory); public/exported callees are
deliberately never recorded as edges here (see `build_call_graph`), which
is what makes `closure` naturally stop expanding at the public-API boundary
without any extra bookkeeping.

Best-effort, name-based resolution over `frob.lang.RawSymbol.body_tokens`
(a flat leaf-token stream, no scope/overload info) -- two same-named
private helpers in different files of the same package can alias; this is
a triage aid, not a soundness guarantee, matching every other rung in
`frob.dup` (docs/modules/dup.md's no-silent-fallback rule only applies to
frob_core-dependent rungs, not to this best-effort resolution step).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = [
    "UNRESOLVED_CALLEE",
    "CallGraph",
    "build_call_graph",
    "build_reference_graph",
    "closure",
]

_DEFAULT_MAX_DEPTH = 3
_DEFAULT_MAX_NODES = 12

# frob:doc docs/modules/graph.md#call-graph
# frob:ticket T-0809
# A sentinel callee symref `build_call_graph` wires into `CallGraph.calls`
# (see `_resolve_edges`'s `mark_unresolved` branch) the moment a call site's
# target LOOKS like it should resolve locally under this module's own
# private-symbol naming convention (a leading underscore) but has zero
# candidates in the by-name index -- e.g. a helper renamed/removed, or one
# defined outside the `paths` this build was scoped to. `frob.graph.summary`
# (T-0745) consumes this exact string as its poisoning sentinel; defined
# here (not there) because `callgraph` has no dependency on `summary`, and
# `summary` already depends on `callgraph` -- `summary.UNRESOLVED_CALLEE`
# re-exports this same object for backward compatibility, never a second
# divergent sentinel string.
UNRESOLVED_CALLEE = "?unresolved"


# frob:doc docs/modules/graph.md#call-graph
class CallGraph(BaseModel):
    """Caller symref -> callee symref edges, PRIVATE callees only.

    Only private/module-local callees are ever recorded (see
    `build_call_graph`), so a BFS `closure` over this graph stops expanding
    at any public API boundary for free -- there is simply no edge to
    follow past it.
    """

    model_config = ConfigDict(frozen=True)

    calls: Mapping[str, tuple[str, ...]] = {}


def _short_name(qualname: str) -> str:
    """The final dotted component of a qualname (`Class.method` -> `method`)."""
    return qualname.rsplit(".", 1)[-1]


# T-0583: `memoize_per_run`/`functools.wraps`-style decorator wrappers take
# the REAL callee as a bare argument (`memoize_per_run(_parse_file_uncached)`)
# rather than ever naming it in a `name(` call token of its own -- the wrap
# happens at the wrapper's call site, not the wrapped function's. Any of
# these markers, called with a single bare-identifier argument, means that
# argument's own edges belong to the caller just as if it had been called
# directly.
# frob:ticket T-0583
_WRAPPER_MARKER_NAMES = frozenset({"memoize_per_run", "wraps", "lru_cache", "cache"})


# frob:ticket T-0583
def _called_names(body_tokens: tuple[str, ...]) -> frozenset[str]:
    """Identifier tokens immediately followed by `(` -- a best-effort call
    scan -- PLUS (T-0583) the bare-identifier argument to a known decorator/
    memoization wrapper marker (`_WRAPPER_MARKER_NAMES`), which is never
    itself followed by `(` (it is passed BY REFERENCE to the wrapper, not
    called) but is functionally reached the same way a direct call would be:
    `memoize_per_run(_target)` makes every subsequent invocation of the
    wrapper's result behave exactly like calling `_target`."""
    names: set[str] = set()
    for i in range(len(body_tokens) - 1):
        tok = body_tokens[i]
        if body_tokens[i + 1] == "(" and tok.isidentifier():
            names.add(tok)
            if (
                tok in _WRAPPER_MARKER_NAMES
                and i + 2 < len(body_tokens)
                and body_tokens[i + 2].isidentifier()
                and (i + 3 >= len(body_tokens) or body_tokens[i + 3] in (")", ","))
            ):
                names.add(body_tokens[i + 2])
    return frozenset(names)


# frob:ticket T-0565
def _called_names_from_sym(sym) -> frozenset[str]:  # noqa: ANN001
    """`_called_names` over `sym.body_tokens` -- the `build_call_graph`
    extractor, unchanged from before T-0565 (a call happens in a body, not
    a signature)."""
    return _called_names(sym.body_tokens)


# frob:ticket T-0422
# frob:ticket T-0565
def _referenced_names(sym) -> frozenset[str]:  # noqa: ANN001
    """Every bare identifier token in `sym`'s signature AND body, called or
    not -- broader recall than `_called_names`: also catches a dispatch-
    table/registry reference (`{"cmd": _foo}`), a decorator target, or a
    parameter default that never appears as a `name(...)` call token at
    all.

    T-0565: `sig_tokens` joins `body_tokens` here (previously body-only),
    closing two systematic DEAD001 false-positive classes the T-0422 Done
    report catalogued: (1) a module-level `CONST`/`TYPE` symbol (e.g. a
    dispatch dict `_DISPATCH_BY_TYPE = {"cpp": _dispatch_check_cpp, ...}`)
    has NO body at all (`RawSymbol.body_tokens` is always `()` for these
    kinds -- see `_walk_python._const_symbol`) but its right-hand-side
    tokens, including any referenced private helper, live in `sig_tokens`
    (the walker tokenizes the WHOLE assignment statement into `sig_tokens`
    for a const); (2) a pytest fixture referenced only by PARAMETER NAME
    from a sibling test function (`def test_x(_repo_root): ...`) is a bare
    identifier in that test function's own SIGNATURE, not its body --
    `sig_tokens` is exactly where a parameter list lives. Kept as a
    separate function from `_called_names_from_sym` (rather than one
    shared body+sig extractor) because `build_call_graph`'s callers
    (`frob.dup`'s helper-inline triage) reason about "called", not
    "mentioned anywhere", and widening its recall would change unrelated
    behavior no ticket asked for."""
    return frozenset(
        tok for tok in (*sym.sig_tokens, *sym.body_tokens) if tok.isidentifier()
    )


def _parse_package(root: Path, paths: Sequence[str]) -> dict[str, list]:
    """`path -> [RawSymbol, ...]` for every file in `paths` that parses
    cleanly -- the shared indexing phase `build_call_graph` and
    `build_reference_graph` both start from."""
    from frob.lang import parse_file

    parsed_by_path: dict[str, list] = {}
    for path in paths:
        result = parse_file(root / path)
        if result.is_err:
            continue
        parsed_by_path[path] = list(result.danger_ok.symbols)
    return parsed_by_path


# frob:doc docs/modules/graph.md#call-graph
# frob:invariant INV-014
# frob:ticket T-0809
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_marks_unresolved_private_looking_callee  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_does_not_mark_unresolved_public_looking_call  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_default_preserves_old_silent_omission_behavior  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_resolved_private_callee_is_not_also_unresolved  # noqa: E501
def build_call_graph(
    root: Path, paths: Sequence[str], *, mark_unresolved: bool = False
) -> CallGraph:
    """Build the intra-file + intra-package call graph over `paths`.

    `paths` are repo-root-relative POSIX file paths (typically every
    language-supported file in one package/directory). A call token
    resolves to a callee symbol only when the callee's short name starts
    with `_` (private/module-local -- never a re-exported public symbol),
    in the same file or another file under `paths`. This is deliberate,
    not just an optimization: a call to a PUBLIC symbol is never recorded
    as an edge here, which is what makes `closure` stop expanding at the
    public-API boundary automatically (see `CallGraph`'s docstring).
    Ambiguous same-name matches within the allowed candidate set all get
    an edge (best-effort; `closure` node-caps the fan-out).

    T-0809: when `mark_unresolved` (default `False`), a call target that
    LOOKS like it should resolve under this module's own private-symbol
    convention (its short name starts with `_`) but matches zero
    candidates in the by-name index gets a `UNRESOLVED_CALLEE` edge
    instead of being silently dropped -- this is what lets
    `frob.graph.summary.compute_protocol_summaries` poison a real
    caller's summary on a genuinely unresolved private call, not just a
    fixture-fabricated one. A call to a name that never looked local in
    the first place (no leading underscore -- a builtin, stdlib, or
    third-party call) is never marked unresolved; that omission is
    unchanged, deliberate best-effort scope, not a gap this ticket closes.

    Defaults to `False` (opt-in), NOT `True`: `frob.gates` and
    `frob.dup._pipeline` already call `build_call_graph` and feed its
    output (including `closure()` over it) straight through code that
    assumes every entry is a real `path::qualname` symref -- a bare
    `UNRESOLVED_CALLEE` sentinel breaks that assumption (observed as an
    `IndexError` in `frob.gates._cov006_third_file_reachable`'s
    `helper_symref.split("::", 1)[1]` during this ticket's own gate pass).
    Widening every existing caller's behavior silently is out of this
    ticket's scope (`src/frob/gates/**`, `src/frob/dup/**` are not in
    `scope`); a future caller that wants poisoning-aware resolution (e.g.
    a real `compute_protocol_summaries` integration) opts in explicitly.
    """
    parsed_by_path = _parse_package(root, paths)
    by_name = _short_name_index(parsed_by_path)
    calls = _resolve_edges(
        parsed_by_path, by_name, _called_names_from_sym, mark_unresolved=mark_unresolved
    )
    return CallGraph(calls=calls)


# frob:doc docs/modules/graph.md#call-graph
# frob:ticket T-0422
# frob:tests tests/test_graph.py::TestCallGraph.test_build_reference_graph_catches_dispatch_table_entry  # noqa: E501
def build_reference_graph(root: Path, paths: Sequence[str]) -> CallGraph:
    """Like `build_call_graph`, but records a private symbol as REFERENCED
    the moment another symbol's body names it at all -- a dispatch-table
    entry (`COMMANDS = {"new": _new}`) or decorator target, not only a
    `name(...)` call token. Strictly broader recall than `build_call_graph`
    (same `CallGraph` shape, reused rather than inventing a parallel
    model) -- T-0422's dead-symbol gate needs "is this symbol referenced
    anywhere", not strictly "called", since a symbol wired only via a
    dispatch table would otherwise look identical to genuinely dead code
    under `build_call_graph` alone."""
    parsed_by_path = _parse_package(root, paths)
    by_name = _short_name_index(parsed_by_path)
    # T-0809: `mark_unresolved=False` here, deliberately -- "referenced but
    # unbound" is a much weaker/noisier signal than "called but unbound"
    # (`_referenced_names` includes every bare identifier, not just call
    # tokens), and `build_reference_graph`'s only consumer (T-0422's dead-
    # symbol gate) has no poisoning semantics to feed; widening it would
    # just be unused edges, not a real gap this ticket's scope covers.
    refs = _resolve_edges(
        parsed_by_path, by_name, _referenced_names, mark_unresolved=False
    )
    return CallGraph(calls=refs)


# frob:ticket T-0361
def _short_name_index(
    parsed_by_path: dict[str, list],
) -> dict[str, list[tuple[str, str, bool]]]:
    """`short_name -> [(symref, path, is_private)]` index over every symbol
    in `parsed_by_path`; split out of `build_call_graph`'s indexing phase
    (T-0361)."""
    by_name: dict[str, list[tuple[str, str, bool]]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            symref = f"{path}::{sym.qualname}"
            is_private = _short_name(sym.qualname).startswith("_")
            by_name.setdefault(_short_name(sym.qualname), []).append(
                (symref, path, is_private)
            )
    return by_name


# frob:ticket T-0361
# frob:ticket T-0422
# frob:ticket T-0809
def _resolve_edges(
    parsed_by_path: dict[str, list],
    by_name: dict[str, list[tuple[str, str, bool]]],
    name_extractor,
    *,
    mark_unresolved: bool = False,
) -> dict[str, tuple[str, ...]]:
    """Caller symref -> resolved private-callee symrefs, per `build_call_graph`'s
    resolution rule (never a public symbol, never self); split out of
    `build_call_graph`'s edge-resolution phase (T-0361). `name_extractor`
    (T-0422: `_called_names_from_sym` for `build_call_graph`,
    `_referenced_names` for `build_reference_graph`) is the only thing
    that differs between the two graphs -- everything else (the by-name
    index, the private/self filtering) is shared. `name_extractor` takes
    the whole `sym` (T-0565, not just `sym.body_tokens`) so it can choose
    which token field(s) to scan -- `_referenced_names` needs both
    `sig_tokens` and `body_tokens`.

    T-0809: `mark_unresolved` -- when a scanned `name` starts with `_`
    (looks like our own private-symbol naming convention) but resolves to
    zero candidates in `by_name` at all (not merely zero PRIVATE
    candidates -- a name matching only public/ambiguous entries is a
    normal miss, not evidence of a broken local reference), the caller
    gets one `UNRESOLVED_CALLEE` edge appended instead of that name being
    silently dropped. Appended at most once per caller regardless of how
    many distinct unresolved private-looking names it has, matching
    `frob.graph.summary`'s treatment of the sentinel as a poisoning FLAG,
    not a per-callee enumeration.
    """
    calls: dict[str, tuple[str, ...]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            caller_symref = f"{path}::{sym.qualname}"
            names = name_extractor(sym)
            callees: list[str] = []
            saw_unresolved = False
            for name in names:
                candidates = by_name.get(name, ())
                matched_private = False
                for symref, _cand_path, is_private in candidates:
                    if symref == caller_symref:
                        continue
                    if is_private:
                        callees.append(symref)
                        matched_private = True
                if (
                    mark_unresolved
                    and not matched_private
                    and not candidates
                    and name.startswith("_")
                ):
                    saw_unresolved = True
            if saw_unresolved:
                callees.append(UNRESOLVED_CALLEE)
            if callees:
                calls[caller_symref] = tuple(callees)
    return calls


# frob:doc docs/modules/graph.md#call-graph
def closure(
    graph: CallGraph,
    start: str,
    *,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_nodes: int = _DEFAULT_MAX_NODES,
) -> tuple[str, ...]:
    """Bounded BFS closure of `start`'s private-callee reachable set.

    Depth-limited (`max_depth` hops), cycle-guarded (a visited set, so a
    mutual-recursion pair never loops), and node-count-capped
    (`max_nodes` -- stops enqueueing once the cap is hit; already-included
    nodes are kept, never partially retracted). Public callees are never
    in `graph.calls` at all (see `build_call_graph`), so the walk stops at
    the public-API boundary automatically. Returns callees in BFS
    (breadth-first, shallow-first) order, `start` itself excluded.
    """
    visited: set[str] = {start}
    order: list[str] = []
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    while queue and len(order) < max_nodes:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for callee in graph.calls.get(node, ()):
            if callee in visited:
                continue
            visited.add(callee)
            order.append(callee)
            if len(order) >= max_nodes:
                break
            queue.append((callee, depth + 1))
    return tuple(order[:max_nodes])
