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
    "OrderedCallGraph",
    "PrivateHelperGap",
    "build_call_graph",
    "build_ordered_call_graph",
    "build_reference_graph",
    "closure",
    "scope_private_helper_gaps",
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


# frob:doc docs/modules/graph.md#call-graph
# frob:ticket T-0840
class OrderedCallGraph(BaseModel):
    """Caller symref -> callee symrefs IN STATEMENT ORDER (T-0840), the
    ordered counterpart to `CallGraph`. Same private-callee-only
    resolution rule as `CallGraph` (see `build_call_graph`'s docstring),
    but `calls[caller]` here is a TUPLE preserving the source-text order
    each call token appears in (duplicates kept -- calling the same
    private helper twice yields two entries, one per call site), not an
    unordered/deduplicated set. This is what lets a consumer (T-0840's
    `frob.gates._protocol_summary` ordering check) ask "what has this
    function already called BEFORE this exact call site" -- a question
    `CallGraph`'s unordered edge set cannot answer at all.

    DISCLOSED SCOPE: order here is purely the LINEAR order call tokens
    appear in `RawSymbol.body_tokens` (a flat leaf-token stream with no
    control-flow structure) -- a call inside an `if`/`else` branch, a
    loop, or after a `return` is indistinguishable from one that always
    executes. This is "sequential-order-sensitive", not fully
    "path-sensitive" over branches; the ticket-named crisp win (catching a
    call to a `frob:requires`-tagged function made BEFORE the transition
    that establishes its precondition, within one caller's own body) is
    real and sound in the no-branching case, and conservative
    (never a false accusation) whenever branches interleave the calls --
    see `frob.gates._protocol_summary`'s PROTO004 docstring for how this
    gets used and what remains an approximation."""

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


# frob:ticket T-0840
def _ordered_called_names(body_tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Like `_called_names`, but returns call-token NAMES in the STATEMENT
    ORDER they appear in `body_tokens` (duplicates kept, one entry per
    occurrence) instead of collapsing into an unordered `frozenset` --
    `build_ordered_call_graph`'s (T-0840) extractor. `_called_names` itself
    is unchanged (still frozenset-based; every existing caller of
    `build_call_graph` keeps its current unordered contract) -- this is a
    parallel extractor, not a replacement, because widening
    `build_call_graph`'s own output shape would ripple through every
    existing consumer (`frob.dup`, `frob.gates._dead_symbols`,
    `frob.gates._protocol_summary`'s PROTO001/002/003) for no benefit to
    them; only a caller that actually wants per-call-site ordering
    (T-0840's `frob.gates._protocol_summary` ordering check) builds the
    ordered graph instead.

    T-0930 DISCLOSURE: a `frob_core`-backed native version of this scan
    was prototyped and measured SLOWER than this pure-Python loop (0.242s
    vs 0.135s median, dead_symbols in-scope thread_time over this repo's
    own `src/frob/gates` package, docs/audits/check-performance.md's
    remediation log) -- per-symbol PyO3 marshaling overhead dominates at
    this call granularity (thousands of small per-symbol calls), unlike
    `_resolve_edges`'s native path (46 large, batched calls, a genuine
    win). Not wired; kept pure-Python deliberately, not by omission."""
    names: list[str] = []
    for i in range(len(body_tokens) - 1):
        tok = body_tokens[i]
        if body_tokens[i + 1] == "(" and tok.isidentifier():
            names.append(tok)
            if (
                tok in _WRAPPER_MARKER_NAMES
                and i + 2 < len(body_tokens)
                and body_tokens[i + 2].isidentifier()
                and (i + 3 >= len(body_tokens) or body_tokens[i + 3] in (")", ","))
            ):
                names.append(body_tokens[i + 2])
    return tuple(names)


# frob:ticket T-0583
def _called_names(body_tokens: tuple[str, ...]) -> frozenset[str]:
    """Identifier tokens immediately followed by `(` -- a best-effort call
    scan -- PLUS (T-0583) the bare-identifier argument to a known decorator/
    memoization wrapper marker (`_WRAPPER_MARKER_NAMES`), which is never
    itself followed by `(` (it is passed BY REFERENCE to the wrapper, not
    called) but is functionally reached the same way a direct call would be:
    `memoize_per_run(_target)` makes every subsequent invocation of the
    wrapper's result behave exactly like calling `_target`.

    T-0930 DISCLOSURE: same "prototyped a native version, measured it
    SLOWER, kept pure-Python" disposition as `_ordered_called_names`
    above -- see that docstring."""
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


# frob:ticket T-0813
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_exempts_super_dunder_call_from_unresolved  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_call_graph_still_marks_unresolved_self_attribute_call  # noqa: E501
def _unresolved_exempt_names(body_tokens: tuple[str, ...]) -> frozenset[str]:
    """Names whose EVERY call-token occurrence in `body_tokens` is an
    attribute call (`<expr>.name(`) on something other than `self` --
    T-0813's disposition of the dominant real-repo `UNRESOLVED_CALLEE`
    false-positive class the T-0809 reviewer flagged before production
    wiring: `obj._method(...)` and `super().__init__(...)` both LOOK like
    this module's own private-symbol calling convention (leading
    underscore) but are never actually a call to a local helper this
    best-effort, name-based graph could ever resolve -- `obj`/`super()`'s
    real target lives in a different class or a completely different
    package this run's `paths` may not even include. `self._foo(...)` is
    NOT exempted (that receiver token IS the enclosing class -- exactly
    the intra-package private-helper call this graph is meant to catch)
    -- only checked against the token immediately preceding the `.`, so a
    chained call (`self._helper()._foo()`) is conservatively exempted too
    (its receiver is not literally the token `self`); a rare miss, never
    a false accusation, matching this module's best-effort posture
    elsewhere. Same miss for `cls._x(...)` inside a classmethod -- `cls`
    is exactly as much "the enclosing class" as `self` is for an
    intra-package private-helper call, but this check only ever
    recognizes the literal token `self`, so a classmethod's own private
    calls via `cls.` are conservatively exempted too (never a false
    accusation, just a narrower catch than `self.` gets). A name that
    ALSO appears as a bare call or a `self.`-call somewhere else in the
    same body is not exempt -- one confident occurrence is enough to
    keep it eligible for unresolved marking.

    T-0930 DISCLOSURE: same "prototyped a native version, measured it
    SLOWER, kept pure-Python" disposition as `_ordered_called_names`
    above -- see that docstring."""
    confident: set[str] = set()
    all_calls: set[str] = set()
    for i in range(len(body_tokens) - 1):
        tok = body_tokens[i]
        if body_tokens[i + 1] != "(" or not tok.isidentifier():
            continue
        all_calls.add(tok)
        is_attr_call = i > 0 and body_tokens[i - 1] == "."
        receiver_is_self = is_attr_call and i > 1 and body_tokens[i - 2] == "self"
        if not is_attr_call or receiver_is_self:
            confident.add(tok)
    return frozenset(all_calls - confident)


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
    behavior no ticket asked for.

    T-0930 DISCLOSURE: this was profiled as `dead_symbols`'s new dominant
    cost once `_resolve_edges`'s own matching loop was moved onto
    `frob_core` (docs/audits/check-performance.md's remediation log) --
    a native version was prototyped, but measured SLOWER end-to-end
    (0.242s vs 0.135s median dead_symbols in-scope thread_time) because
    this function is called once PER SYMBOL (thousands of small calls
    over a real package), unlike `_resolve_edges`'s 46 large batched
    calls -- per-call PyO3 marshaling overhead dominates any win from the
    Rust loop itself at this granularity. Kept pure-Python deliberately;
    see `_ordered_called_names`'s docstring for the same disposition."""
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
    resolves to a callee symbol only when `frob.lang.RawSymbol.public` is
    `False` for that callee (T-0841: each grammar walker's OWN,
    language-correct publicness rule -- Python's leading underscore,
    Rust's `pub`/PyO3-export, C++'s `access_specifier`/file-scope
    `static`, TypeScript's `export`/`accessibility_modifier`; see
    `_short_name_index`), in the same file or another file under `paths`.
    This is deliberate, not just an optimization: a call to a PUBLIC
    symbol is never recorded as an edge here, which is what makes
    `closure` stop expanding at the public-API boundary automatically
    (see `CallGraph`'s docstring). Ambiguous same-name matches within the
    allowed candidate set all get an edge (best-effort; `closure`
    node-caps the fan-out).

    T-0809: when `mark_unresolved` (default `False`), a call target that
    LOOKS like it should resolve under Python's leading-underscore naming
    convention (its short name starts with `_`) but matches zero
    candidates in the by-name index gets a `UNRESOLVED_CALLEE` edge
    instead of being silently dropped -- this is what lets
    `frob.graph.summary.compute_protocol_summaries` poison a real
    caller's summary on a genuinely unresolved private call, not just a
    fixture-fabricated one. A call to a name that never looked local in
    the first place (no leading underscore -- a builtin, stdlib, or
    third-party call) is never marked unresolved; that omission is
    unchanged, deliberate best-effort scope, not a gap this ticket closes.
    T-0841 DISCLOSURE: this `mark_unresolved` heuristic is still
    Python-naming-specific (it scans the CALLED NAME's spelling, which is
    all a flat token stream offers -- unlike `_short_name_index`'s
    resolution side, there is no `RawSymbol` for an unresolved callee to
    read `.public` off of) -- a Rust/C++/TypeScript file with a genuinely
    dangling private call whose name does not happen to start with `_`
    will not be flagged unresolved. This is the same false-negative-biased
    direction every other best-effort rung in this module already accepts
    (never a false accusation, just a narrower catch outside Python) and
    is not closed by this ticket -- `mark_unresolved`'s per-language
    naming heuristics remain future work.

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
        parsed_by_path,
        by_name,
        _called_names_from_sym,
        mark_unresolved=mark_unresolved,
        # T-0813: only `build_call_graph`'s call-token extraction has the
        # attribute-call context `_unresolved_exempt_names` needs (a
        # `sym.body_tokens` flat stream); `build_reference_graph` always
        # passes `mark_unresolved=False` so it never consults this at all.
        exempt_extractor=(
            (lambda sym: _unresolved_exempt_names(sym.body_tokens))
            if mark_unresolved
            else None
        ),
    )
    return CallGraph(calls=calls)


# frob:doc docs/modules/graph.md#call-graph
# frob:ticket T-0840
# frob:tests tests/test_graph.py::TestCallGraph.test_build_ordered_call_graph_preserves_source_text_call_order  # noqa: E501
# frob:tests tests/test_graph.py::TestCallGraph.test_build_ordered_call_graph_resolves_a_rust_private_callee  # noqa: E501
def build_ordered_call_graph(root: Path, paths: Sequence[str]) -> OrderedCallGraph:
    """`build_call_graph`'s ordered counterpart (T-0840): same private-
    callee-only resolution rule (a callee resolves only when
    `RawSymbol.public` is `False`, T-0841), but `calls[caller]` preserves
    the source-text order call tokens appear in, duplicates included,
    instead of collapsing into an unordered set. No `mark_unresolved`
    parameter -- an ordering-sensitive consumer (T-0840's PROTO004) treats
    a genuinely unresolved name the same conservative way `_resolve_edges`
    already treats a name matching zero candidates: it contributes no
    callee-summary information for anything AFTER it (see
    `frob.gates._protocol_summary._ordered_call_sites`'s poisoning-halts-
    the-walk posture), so no sentinel edge is needed in the ordered shape
    itself."""
    parsed_by_path = _parse_package(root, paths)
    by_name = _short_name_index(parsed_by_path)
    calls: dict[str, tuple[str, ...]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            caller_symref = f"{path}::{sym.qualname}"
            callees: list[str] = []
            for name in _ordered_called_names(sym.body_tokens):
                for symref, _cand_path, is_private in by_name.get(name, ()):
                    if symref == caller_symref or not is_private:
                        continue
                    callees.append(symref)
            if callees:
                calls[caller_symref] = tuple(callees)
    return OrderedCallGraph(calls=calls)


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
# frob:ticket T-0841
def _short_name_index(
    parsed_by_path: dict[str, list],
) -> dict[str, list[tuple[str, str, bool]]]:
    """`short_name -> [(symref, path, is_private)]` index over every symbol
    in `parsed_by_path`; split out of `build_call_graph`'s indexing phase
    (T-0361).

    T-0841: `is_private` is `not sym.public` -- `RawSymbol.public` is each
    `frob.lang` grammar walker's OWN, language-correct publicness rule
    (Python's leading underscore, Rust's `pub`/PyO3-export, C++'s
    `access_specifier`/file-scope `static`, TypeScript's `export`/
    `accessibility_modifier` -- see `frob.lang._walk_*`), not a re-derived
    naming heuristic. Before T-0841 this index recomputed privacy via
    `_short_name(sym.qualname).startswith("_")`, which happens to equal
    `sym.public` for Python (`_walk_python.py`'s own rule is exactly that
    check) but is simply wrong for every other supported grammar (Rust
    privacy is scoping, not spelling; C++'s is `private:`/`static`;
    TypeScript's is `export`) -- `build_call_graph`/`build_reference_graph`
    were therefore silently Python-only in practice despite parsing every
    language `frob.lang.parse_file` supports. Switching to the walker's own
    `public` field is what actually wires Rust/C++/TypeScript into a real
    call-graph scan (the T-0841 ask), not a new call-graph implementation
    per language."""
    by_name: dict[str, list[tuple[str, str, bool]]] = {}
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            symref = f"{path}::{sym.qualname}"
            is_private = not sym.public
            by_name.setdefault(_short_name(sym.qualname), []).append(
                (symref, path, is_private)
            )
    return by_name


# frob:ticket T-0361
# frob:ticket T-0422
# frob:ticket T-0809
# frob:ticket T-0930
def _resolve_edges(
    parsed_by_path: dict[str, list],
    by_name: dict[str, list[tuple[str, str, bool]]],
    name_extractor,
    *,
    mark_unresolved: bool = False,
    exempt_extractor=None,  # noqa: ANN001
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

    T-0813: `exempt_extractor(sym)`, when given, returns the subset of
    `names` that `mark_unresolved` must NOT count toward the unresolved
    flag even when they are otherwise zero-candidate private-looking
    names -- `build_call_graph`'s `obj._method(...)`/`super().__init__
    (...)` false-positive disposition (`_unresolved_exempt_names`).
    `None` (the default, and `build_reference_graph`'s always-`False`
    posture) exempts nothing, unchanged prior behavior.

    T-0930 DISCLOSURE: a `frob_core.resolve_call_edges` native port of
    this matching loop was built, parity-tested, and BENCHMARKED
    end-to-end on `dead_symbols` (docs/audits/check-performance.md
    rust-candidate row 8) -- measured NET SLOWER than staying pure-Python
    (0.164s vs 0.127s median in-scope thread_time over this repo's own
    `src/frob/gates` package, `dead_symbols` calls this once per package,
    46 packages here). At this repo's real per-package data scale (tens
    of symbols, hundreds of `by_name` candidates), the PyO3 marshaling
    cost of crossing the whole `by_name` index and per-caller name lists
    into Rust and reconstructing the result dict outweighs the matching
    loop's own (already small) pure-Python cost -- this loop was never
    dead_symbols' actual dominant cost once `_referenced_names`'s own
    token-scan overhead (the real dominant cost, see that function's
    docstring) is accounted for separately. NOT dispatched to native by
    default for this reason -- `frob.graph._core.resolve_call_edges_native`
    stays available (parity-tested against `_resolve_edges_python`,
    tests/test_graph.py::TestResolveCallEdgesNative) for a future caller
    with a genuinely large single-batch input (e.g. a whole-repo call
    graph in one call, not once per small package) where the fixed
    marshaling cost amortizes over enough matching work to win."""
    callers: list[str] = []
    names_per_caller: list[list[str]] = []
    exempt_per_caller: list[list[str]] = []
    for path, symbols in parsed_by_path.items():
        for sym in symbols:
            callers.append(f"{path}::{sym.qualname}")
            names_per_caller.append(list(name_extractor(sym)))
            exempt_per_caller.append(
                list(exempt_extractor(sym)) if exempt_extractor is not None else []
            )

    return _resolve_edges_python(
        callers,
        names_per_caller,
        exempt_per_caller,
        by_name,
        mark_unresolved=mark_unresolved,
    )


# frob:ticket T-0930
# frob:ticket T-0972
def _resolve_edges_python(
    callers: list[str],
    names_per_caller: list[list[str]],
    exempt_per_caller: list[list[str]],
    by_name: dict[str, list[tuple[str, str, bool]]],
    *,
    mark_unresolved: bool = False,
) -> dict[str, tuple[str, ...]]:
    """Pure-Python fallback for `_resolve_edges`'s matching loop -- kept
    byte-identical to the pre-T-0930 implementation (same double loop over
    parallel per-caller name/exempt lists against the shared `by_name`
    index), used whenever `frob_core` is unavailable
    (`frob.graph._core.core_available` is `False`). Never called directly
    outside `_resolve_edges` and its own golden-parity test."""
    calls: dict[str, tuple[str, ...]] = {}
    for caller_symref, names, exempt in zip(
        callers, names_per_caller, exempt_per_caller
    ):
        callees: list[str] = []
        saw_unresolved = False
        for name in names:
            candidates = by_name.get(name, ())
            matched_private = False
            # frob:waive PERF003 reason="candidates are already partitioned per name via by_name; total work across all names is O(total candidates), not a cross join"  # noqa: E501
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
                and name not in exempt
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


# frob:doc docs/modules/graph.md#scope-closure-t-0998
class PrivateHelperGap(BaseModel):
    """T-0998 direction (3): a scoped caller calls a private/module-local
    helper (`callee`) defined in a file NOT in the ticket's declared
    scope -- probable under-capture, since the caller will likely need to
    touch `callee` too. `only_used_by_scope` is `True` when every OTHER
    caller of `callee` this scan saw is also inside scope, which is the
    strong "just add `definition_file` to scope" case rather than merely
    "review this dependency"."""

    model_config = ConfigDict(frozen=True)

    caller: str
    callee: str
    definition_file: str
    only_used_by_scope: bool


def _file_of(symref: str) -> str:
    """The file half of a `path::qualname` symref -- shared by
    `scope_private_helper_gaps`'s caller/callee-side lookups."""
    return symref.split("::", 1)[0]


def _short_name_of_symref(symref: str) -> str:
    """The bare short name half of a `path::qualname` symref (T-1012) --
    `_short_name` applied to the qualname side, shared by
    `scope_private_helper_gaps`'s same-name-collision check below."""
    return _short_name(symref.split("::", 1)[-1])


# frob:doc docs/modules/graph.md#scope-closure-t-0998
# frob:ticket T-0998
# frob:tests tests/test_graph.py::TestScopePrivateHelperGaps.test_flags_scoped_caller_of_unscoped_private_helper  # noqa: E501
# frob:tests tests/test_graph.py::TestScopePrivateHelperGaps.test_only_used_by_scope_true_when_no_external_caller  # noqa: E501
# frob:tests tests/test_graph.py::TestScopePrivateHelperGaps.test_clean_when_callee_also_in_scope  # noqa: E501
# frob:tests tests/test_graph.py::TestScopePrivateHelperGaps.test_flat_dir_same_name_self_match_is_silent  # noqa: E501
# frob:tests tests/test_graph.py::TestScopePrivateHelperGaps.test_flat_dir_genuine_cross_file_helper_still_fires  # noqa: E501
def scope_private_helper_gaps(
    root: Path, scope: tuple[str, ...] | list[str], files: Sequence[str]
) -> tuple[PrivateHelperGap, ...]:
    """T-0998 direction (3): build the private-callee `CallGraph`
    (`build_call_graph`, the shared substrate T-0288/T-0290 already use --
    no second traversal engine) over `files` restricted to the SAME
    directories `scope` actually matches, then flag every scoped caller's
    edge to a private callee whose own file is NOT in scope. `files` is
    the repo-relative file list to consider (callers pass
    `GraphSnapshot.file_hashes`'s keys -- already-hashed, no extra git
    walk needed); restricting `build_call_graph`'s own `paths` argument to
    scope-adjacent directories (rather than the whole repo) keeps this
    bounded the way `build_call_graph`'s own docstring assumes (a
    per-package scan, not a whole-tree one).

    T-1012: over a FLAT top-level directory with hundreds of sibling
    files (`tests/`), "same parent directory as a scoped file" widens
    `candidate_paths` to the whole directory, and `build_call_graph`'s
    bare-short-name matching (by design -- see `_resolve_edges_python`)
    resolves a caller's own local helper call (e.g. `test_perf.py`
    calling ITS OWN `_snapshot`) against EVERY same-named private symbol
    across every sibling file, not just its own -- `test_perf.py::
    test_x -> test_docptr_gate.py::_snapshot` fires purely from name
    collision, not an actual cross-file dependency. Suppressed here by a
    same-short-name same-file check: if `caller`'s own file ALSO defines
    a private symbol under a callee's exact short name, that local
    definition is overwhelmingly the real target in a flat, single-
    directory scan -- every OTHER same-named file's candidate is dropped
    for that name, for this caller, without touching `build_call_graph`'s
    own general (multi-match) resolution semantics other consumers rely
    on. A genuine cross-file private helper (no same-name candidate in
    the caller's own file at all, e.g. `tests/test_B.py` calling a
    helper ONLY `tests/test_A.py` defines) is unaffected and still
    flagged."""
    from frob.tickets._models import scope_matches

    all_files = tuple(files)
    scope_files = {f for f in all_files if scope_matches(f, scope)}
    if not scope_files:
        return ()
    graph = build_call_graph(
        root, _scope_candidate_paths(all_files, scope_files)
    )

    callers_of: dict[str, set[str]] = {}
    for caller, callees in graph.calls.items():
        for callee in callees:
            if callee == UNRESOLVED_CALLEE:
                continue
            callers_of.setdefault(callee, set()).add(caller)

    gaps: list[PrivateHelperGap] = []
    for caller in sorted(graph.calls):
        if _file_of(caller) not in scope_files:
            continue
        gaps.extend(
            _caller_private_helper_gaps(
                caller, graph.calls[caller], scope_files, callers_of
            )
        )
    return tuple(gaps)


def _scope_candidate_paths(
    all_files: tuple[str, ...], scope_files: set[str]
) -> tuple[str, ...]:
    """Every file sharing a parent directory with a scoped file -- the
    scope-adjacent restriction that keeps `scope_private_helper_gaps`'s
    `build_call_graph` call a per-package scan, not a whole-tree one."""
    scope_dirs = {
        _file_of(f).rsplit("/", 1)[0] if "/" in f else "" for f in scope_files
    }
    return tuple(
        f for f in all_files if (f.rsplit("/", 1)[0] if "/" in f else "") in scope_dirs
    )


def _caller_private_helper_gaps(
    caller: str,
    callees: tuple[str, ...],
    scope_files: set[str],
    callers_of: dict[str, set[str]],
) -> list[PrivateHelperGap]:
    """One scoped caller's out-of-scope private-callee gaps, with the
    T-1012 flat-directory suppression applied (see
    `scope_private_helper_gaps`'s docstring for the full rationale)."""
    caller_file = _file_of(caller)
    # T-1012: short names this caller ALSO resolves to a private
    # symbol in its OWN file -- these are same-file self-matches, so
    # any OTHER file's same-named candidate is noise, not a real
    # cross-file dependency, in a flat-directory scan.
    self_resolved_names = {
        _short_name_of_symref(c)
        for c in callees
        if c != UNRESOLVED_CALLEE and _file_of(c) == caller_file
    }
    gaps: list[PrivateHelperGap] = []
    for callee in callees:
        if callee == UNRESOLVED_CALLEE:
            continue
        if _short_name_of_symref(callee) in self_resolved_names:
            continue
        callee_file = _file_of(callee)
        if callee_file in scope_files:
            continue
        other_callers = callers_of.get(callee, set())
        only_scope = all(_file_of(c) in scope_files for c in other_callers)
        gaps.append(
            PrivateHelperGap(
                caller=caller,
                callee=callee,
                definition_file=callee_file,
                only_used_by_scope=only_scope,
            )
        )
    return gaps
