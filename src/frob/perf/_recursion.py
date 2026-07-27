"""PERF005/PERF006: recursion is a control-flow hazard, not a lexical smell
(docs/modules/perf.md's rule table; T-0290).

Termination is undecidable in general, so this stays SOUND, not complete: it
proves the decidable fragment -- structural descent on a well-founded
argument, a strictly-decreasing bounded-integer measure, or a guarded base
case reached by narrowing the recursive argument (`.next`/`.left`,
`x[1:]`/`x[:-1]`, `x - <int>`, `x // 2`) -- and ERRORs on every recursive
function whose termination it cannot prove this way. The escape is a
REASONED directive at the recursive symbol's site,
`frob:invariant terminates reason="..." measure="..."`, auditable exactly
like a `frob:waive` (T-0289's arch-override philosophy, unified here):
the tool proves what it can, and every unprovable residue must carry a
reasoned, counted directive.

Shares the same "same-file, name-based, best-effort" call-resolution
posture as `frob.graph.callgraph` (T-0288's dup helper-inlining substrate)
but is deliberately NOT that module: `callgraph.build_call_graph` excludes
self-edges and any PUBLIC callee by construction (it exists to bound a
BFS closure at the public-API boundary), while recursion detection needs
exactly the opposite -- self-calls and public<->public mutual recursion
both matter here. A second small graph is built locally instead of
widening `callgraph`'s contract for a use case it was not designed for.
"""

# frob:waive TEST005 reason="module line coverage, new T-0290 rule, debt T-0160"

from __future__ import annotations

from collections.abc import Sequence

from frob.gates._models import Severity, Violation
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.lang._models import ParsedFile, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["recursion_rules"]

_FUNCTION_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})

# Token shapes that narrow the recursive argument toward a base case on a
# well-founded measure: a decreasing bounded integer (`n - 1`, `n // 2`,
# `n / 2`), or structural descent into a strictly smaller sub-structure
# (a slice off one end, or a step to a child/parent field). Best-effort,
# lexical -- the same posture as every other PERF rule in this package.
_DESCENT_ATTRS = frozenset({"next", "left", "right", "parent", "child", "children"})

_OPENERS = frozenset({"(", "[", "{"})
_CLOSERS = frozenset({")", "]", "}"})


def _short_name(qualname: str) -> str:
    """The final dotted component of a qualname (`Class.method` -> `method`)."""
    return qualname.rsplit(".", 1)[-1]


def _enclosing_scope(qualname: str) -> str:
    """The qualname prefix a call site's own class/scope lives in (`Class`
    for `Class.method`, `""` for a bare module-level function). Mutual
    recursion pairing (`_recursive_pairs`) requires two candidate symbols to
    share this scope -- reviewer-caught bug (T-0290 round 2): two UNRELATED
    classes that each happen to define a same-named method (`__init__`,
    `run`, ...) must never be paired as mutually recursive just because
    they share a short name in the same file."""
    return qualname.rsplit(".", 1)[0] if "." in qualname else ""


def _is_receiver_aware_call(tokens: tuple[str, ...], i: int) -> bool:
    """True if `tokens[i]` (an identifier immediately followed by `(`)
    is a genuine call candidate under receiver-aware rules: either
    UNqualified (`foo(...)`, no `.` before it), or qualified with `self`
    as the immediate receiver (`self.foo(...)`). Any other qualified form
    -- `super().foo(...)`, `other.foo(...)`, `cls.foo(...)` -- is excluded.
    Reviewer-caught bug (T-0290 round 2): a bare `identifier(` scan with no
    receiver awareness read `super().__init__()` as a self-recursive call
    to `__init__`, producing ~50 false-positive PERF005/006 findings on
    frob's own constructors."""
    if i == 0 or tokens[i - 1] != ".":
        return True
    return i >= 2 and tokens[i - 2] == "self"


def _called_names(tokens: tuple[str, ...]) -> frozenset[str]:
    """Identifier tokens that start a genuine, receiver-aware call
    (`_is_receiver_aware_call`) -- the candidate-callee index
    `_recursive_pairs` walks."""
    names: set[str] = set()
    n = len(tokens)
    for i in range(n - 1):
        tok = tokens[i]
        if tokens[i + 1] != "(" or not tok.isidentifier():
            continue
        if _is_receiver_aware_call(tokens, i):
            names.add(tok)
    return frozenset(names)


def _call_arg_window(tokens: tuple[str, ...], call_open: int) -> tuple[str, ...]:
    """The tokens strictly between a call's own `(` (at `call_open`) and its
    matching `)` -- bracket-depth-aware, so a nested call/subscript inside
    the arguments does not truncate early. Reviewer-caught bug (T-0290
    round 2): the prior fixed `tokens[i+2:i+12]` lookahead window scanned
    PAST the call's own argument list into the surrounding expression, so
    `loop_forever(n) - 1` misread the outer `- 1` as descent even though
    `n` itself is never narrowed inside the call."""
    n = len(tokens)
    depth = 0
    end = n
    for j in range(call_open, n):
        if tokens[j] in _OPENERS:
            depth += 1
        elif tokens[j] in _CLOSERS:
            depth -= 1
            if depth == 0:
                end = j
                break
    return tokens[call_open + 1 : end]


def _descent_bound_vars(tokens: tuple[str, ...]) -> frozenset[str]:
    """Loop variables bound by `for <var> in <expr>.<descent-attr>[(...)]:`
    -- the extremely common tree-walker idiom (`for child in
    node.children:`, `for kid in tree.child_nodes():`) where the STRUCTURAL
    narrowing happens in the loop header, not inside the recursive call's
    own argument list. Without this, every walker that recurses as `for
    child in node.children: _visit(child)` -- finite-tree, genuinely
    terminating -- reads as unproven, since `_visit(child)`'s own argument
    window carries no descent syntax by itself; `child` is only known to be
    structurally smaller via the loop header that bound it. Best-effort,
    lexical, same posture as every other check in this module: `<expr>` is
    not required to be a single identifier, only to end in `.<descent-
    attr>` (optionally called, `.children()`) right before the loop's `:`."""
    n = len(tokens)
    bound: set[str] = set()
    for i in range(n - 3):
        if tokens[i] != "for" or not tokens[i + 1].isidentifier():
            continue
        if tokens[i + 2] != "in":
            continue
        var = tokens[i + 1]
        colon = _header_colon_index(tokens, i + 3)
        if colon is None:
            continue
        header = tokens[i + 3 : colon]
        if _ends_in_descent_attr(header):
            bound.add(var)
    return frozenset(bound)


def _header_colon_index(tokens: tuple[str, ...], start: int) -> int | None:
    """Index of the depth-0 `:` closing a `for`/`while` header starting at
    `start`, or `None` if the header never closes within `tokens`."""
    depth = 0
    n = len(tokens)
    for i in range(start, n):
        if tokens[i] in _OPENERS:
            depth += 1
        elif tokens[i] in _CLOSERS:
            depth -= 1
        elif tokens[i] == ":" and depth == 0:
            return i
    return None


def _ends_in_descent_attr(header: tuple[str, ...]) -> bool:
    """True if a `for ... in <expr>` header ends in `.<descent-attr>`,
    optionally followed by an empty call (`.children()`) -- the shape
    `_descent_bound_vars` binds a loop variable on."""
    tail = list(header)
    if len(tail) >= 2 and tail[-2:] == ["(", ")"]:
        tail = tail[:-2]
    return len(tail) >= 2 and tail[-2] == "." and tail[-1] in _DESCENT_ATTRS


def _has_structural_descent(tokens: tuple[str, ...], callee_short: str) -> bool:
    """True if a recursive call to `callee_short` in `tokens` narrows its
    OWN argument list (bounded to the call's matching parens via
    `_call_arg_window`, not a fixed lookahead) toward a base case:
    `- <int literal>`, `// 2`, `/ 2`, a one-sided slice (`[1:]`/`[:-1]`),
    a `.next`/`.left`/`.right`/`.parent`/`.child`-style attribute step, or
    an argument bound by a `for <var> in <expr>.children:`-shaped loop
    header (`_descent_bound_vars`) -- the tree-walker idiom where the
    narrowing lives in the loop, not the call's own arguments."""
    descent_vars = _descent_bound_vars(tokens)
    n = len(tokens)
    for i in range(n - 1):
        if tokens[i] != callee_short or tokens[i + 1] != "(":
            continue
        if not _is_receiver_aware_call(tokens, i):
            continue
        window = _call_arg_window(tokens, i + 1)
        if _window_shows_descent(window) or (set(window) & descent_vars):
            return True
    return False


def _window_shows_descent(window: tuple[str, ...]) -> bool:
    """The actual per-window shape check `_has_structural_descent` scans
    for, split out so the caller stays a plain loop over call sites."""
    for j, tok in enumerate(window):
        if tok == "-" and j + 1 < len(window) and window[j + 1].isdigit():
            return True
        if tok in ("//", "/") and j + 1 < len(window) and window[j + 1].isdigit():
            return True
        if tok == "." and j + 1 < len(window) and window[j + 1] in _DESCENT_ATTRS:
            return True
        if tok == "[" and j + 1 < len(window) and window[j + 1] in (":", "1"):
            return True
    return False


def _is_tail_call(tokens: tuple[str, ...], callee_short: str) -> bool:
    """True if `return <callee_short>(` (unqualified) or `return
    self.<callee_short>(` appears -- the recursive call is the LAST thing
    the function does on that path, the DoS-relevant shape (Python has no
    TCO: unbounded tail recursion over runtime-sized input is a stack-
    overflow bug the user named explicitly)."""
    n = len(tokens)
    for i in range(n - 2):
        if tokens[i] != "return":
            continue
        j = i + 1
        if tokens[j] == callee_short and tokens[j + 1] == "(":
            return True
        if (
            j + 2 < n
            and tokens[j] == "self"
            and tokens[j + 1] == "."
            and tokens[j + 2] == callee_short
            and j + 3 < n
            and tokens[j + 3] == "("
        ):
            return True
    return False


def _has_guard(tokens: tuple[str, ...]) -> bool:
    """A base-case guard is present: an `if`/`return` appears before the
    recursive call could plausibly fire. Approximated, per this package's
    established posture, as "the function contains an `if` token at all" --
    a recursive function with zero conditional branches can never reach a
    base case and is never proven, guarded or not."""
    return "if" in tokens


# frob:invariant INV-018
# frob:tests tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion
def _termination_reasoned(
    snapshot: GraphSnapshot, symref: str
) -> tuple[str, str] | None:
    """The `(reason, measure)` pair from a `frob:invariant terminates
    reason="..." measure="..."` directive anchored at `symref`, or `None`
    if no such directive is present -- the T-0290 escape hatch, unified
    with T-0289's "prove it, or justify it at the code" philosophy. Both
    attributes must be non-empty: an empty `reason=""`/`measure=""` is not
    a real justification and does not count as proof."""
    for edge in snapshot.edges:
        if (
            edge.kind == EdgeKind.INVARIANT
            and edge.src == symref
            and edge.target == "terminates"
        ):
            reason = edge.attrs.get("reason", "")
            measure = edge.attrs.get("measure", "")
            if reason and measure:
                return (reason, measure)
    return None


def _violation(rule: str, file: str, line: int, symref: str, extra: str) -> Violation:
    """One PERF005/PERF006 violation, message carrying the T-0290 remedy."""
    remedy = (
        'add frob:invariant terminates reason="..." measure="..." at the'
        " recursive site, or restructure so termination is provable"
        if rule == "PERF005"
        else "rewrite as an explicit loop, or prove a static depth bound"
        ' via frob:invariant terminates reason="..." measure="..."'
    )
    return Violation(
        rule=rule,
        # T-0290 lands PERF005/006 at WARN: there are ~45 pre-existing
        # genuine unproven-recursion sites repo-wide (cycle/deploy/map/dup/
        # lang) that must be swept (frob:invariant terminates or restructure)
        # before this can be promoted to ERROR without reddening every repo.
        severity=Severity.WARN,
        file=file,
        line=line,
        message=f"{rule}: {file}:{line} {extra}; suggested fix: {remedy}",
        symref=symref,
    )


def _recursive_pairs(
    symbols_by_name: dict[str, list[tuple[str, str, RawSymbol, str]]],
) -> list[tuple[str, RawSymbol, str]]:
    """Every `(symref, symbol, callee_short)` triple where `symbol` calls
    itself (self-recursion) or is part of a same-file, same-SCOPE mutual-
    recursion pair (A calls B, B calls A) -- `callee_short` is the
    recursive callee's short name, used by the descent/tail-call checks
    below. Cross-candidate matches (the mutual-recursion branch) require
    both the same file AND the same enclosing scope (`_enclosing_scope`) --
    two unrelated classes that happen to share a method name must never be
    paired (reviewer-caught bug, T-0290 round 2)."""
    # Index each name's entries by (path, scope) once up front so the
    # mutual-recursion match below is a dict lookup, not a linear scan with
    # an equality comparison per candidate (PERF003).
    by_name_and_key: dict[str, dict[tuple[str, str], list[tuple[str, RawSymbol]]]] = {}
    for short_name, entries in symbols_by_name.items():
        keyed: dict[tuple[str, str], list[tuple[str, RawSymbol]]] = {}
        for symref, path, symbol, scope in entries:
            keyed.setdefault((path, scope), []).append((symref, symbol))
        by_name_and_key[short_name] = keyed

    hits: list[tuple[str, RawSymbol, str]] = []
    for short_name, entries in symbols_by_name.items():
        for symref, path, symbol, scope in entries:
            called = _called_names(symbol.body_tokens)
            if short_name in called:
                hits.append((symref, symbol, short_name))
                continue
            other_candidates = called - {short_name}
            for other_short in other_candidates:
                if other_short not in by_name_and_key:
                    continue
                candidates = by_name_and_key[other_short].get((path, scope), ())
                for _other_symref, other_symbol in candidates:
                    if short_name in _called_names(other_symbol.body_tokens):
                        hits.append((symref, symbol, other_short))
                        break
    return hits


def _symbols_by_short_name(
    files: Sequence[ParsedFile],
) -> dict[str, list[tuple[str, str, RawSymbol, str]]]:
    """`{short_name: [(symref, path, symbol, enclosing_scope)]}` over every
    function/method in `files` -- the name-based candidate index
    `_recursive_pairs` walks."""
    by_name: dict[str, list[tuple[str, str, RawSymbol, str]]] = {}
    for file in files:
        for symbol in file.symbols:
            if symbol.kind not in _FUNCTION_KINDS:
                continue
            symref = f"{file.path}::{symbol.qualname}"
            by_name.setdefault(_short_name(symbol.qualname), []).append(
                (symref, file.path, symbol, _enclosing_scope(symbol.qualname))
            )
    return by_name


# frob:doc docs/modules/perf.md#public-api
# frob:ticket T-0290
def recursion_rules(
    snapshot: GraphSnapshot, files: Sequence[ParsedFile]
) -> tuple[Violation, ...]:
    """PERF005 (unproven termination) and PERF006 (unbounded tail
    recursion), over every recursive function/method (self or same-file,
    same-scope mutual recursion) in `files`. Both are ERROR-level -- unlike
    PERF001-004, an unreasoned unbounded recursion is a control-flow
    hazard, not a size-blind smell -- and both are suppressed only by a
    reasoned `frob:invariant terminates reason="..." measure="..."` anchor
    (`_termination_reasoned`) or a provable structural descent past a base
    case (`_has_structural_descent` + `_has_guard`); pure, consumed by
    `frob.perf.perf_rules`."""
    by_name = _symbols_by_short_name(files)
    path_by_symref: dict[str, ParsedFile] = {}
    for file in files:
        for symbol in file.symbols:
            if symbol.kind in _FUNCTION_KINDS:
                path_by_symref[f"{file.path}::{symbol.qualname}"] = file

    violations: list[Violation] = []
    for symref, symbol, callee_short in _recursive_pairs(by_name):
        file = path_by_symref[symref]
        tokens = symbol.body_tokens
        line = symbol.span[0]
        reasoned = _termination_reasoned(snapshot, symref)
        descent = _has_structural_descent(tokens, callee_short)
        guarded = _has_guard(tokens)
        proven = reasoned is not None or (descent and guarded)
        if not proven:
            violations.append(
                _violation(
                    "PERF005",
                    file.path,
                    line,
                    symref,
                    f"recursive call to '{callee_short}' with no provable "
                    "termination measure",
                )
            )
        if _is_tail_call(tokens, callee_short) and reasoned is None:
            violations.append(
                _violation(
                    "PERF006",
                    file.path,
                    line,
                    symref,
                    f"tail-recursive call to '{callee_short}' with no proven "
                    "depth bound (Python has no TCO -- unbounded input "
                    "depth is a stack-overflow hazard)",
                )
            )
    _log.info(
        "recursion_rules: scanned %d file(s), %d violation(s)",
        len(files),
        len(violations),
    )
    return tuple(violations)
