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
classes, an `@field_validator`/`@model_validator`-decorated pydantic
validator method (`_is_pydantic_validator`, T-1651 -- pydantic's own
decorator-registry dispatch invokes these, never a call token), an
`@pytest.fixture(autouse=True)` fixture (`_is_autouse_pytest_fixture`,
T-1651 -- moved here from `frob.gates._wire`'s WIRE001, which `_wire.py`
now imports back rather than duplicating; DEAD001 lacked this exemption
entirely before T-1651 and flagged 5 of this repo's own autouse fixtures
as dead), and anything a caller waives with `frob:waive
DEAD001 reason="..."` (the standard mechanism every other advisory-tier
gate in this repo already uses for a case this best-effort token scan cannot
see -- e.g. a handler reached only via `getattr(obj, "_name")` string
dispatch, which never appears as a bare identifier token at all).

WARN-only (advisory-but-tracked, matching REF/PERF/FUZZ's posture) --
never blocks a build on its own, but every finding must eventually be
fixed (wire it or delete it) or waived with an honest reason.

Python (`.py`) files ONLY in this pass -- see `dead_symbol_gate`'s
docstring for why Rust/TypeScript/C are excluded (a real soundness gap
in the shared `frob.graph.callgraph` substrate's privacy detection, not
a scope choice of convenience).

The WIRE001/WIRE002 family that used to share this module moved to
`frob.gates._wire` (T-1420, LARGE001 residue burndown) -- this module
now holds DEAD001 only. `_CALLABLE_KINDS`/`_is_dunder`/`_is_test_symbol`
stay here and are imported back by `_wire.py` (both gates need the same
dunder/test-symbol exemption logic).
"""

from __future__ import annotations

import ast
import re
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


# frob:ticket T-1510
_AUTOUSE_FIXTURE_RE = re.compile(
    r"@(?:pytest\.fixture|pytest_asyncio\.fixture)\s*\([^)]*\bautouse\s*=\s*True",
    re.DOTALL,
)


# frob:ticket T-1510
# frob:ticket T-1652
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _AUTOUSE_FIXTURE_RE.search, a compiled-regex search over an already-caught \
# read_text() output; a compiled pattern search cannot raise"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for lines[start - 1 : end], a list SLICE \
# (never raises KeyError, or any exception, for any start/end) that the resolver's \
# syntactic bracket scan cannot distinguish from a dict lookup"
def _is_autouse_pytest_fixture(root: Path, record) -> bool:
    """True if `record`'s span opens with an `@pytest.fixture(autouse=True)`
    (or `pytest_asyncio.fixture`) decorator -- pytest's own fixture-injection
    machinery invokes an autouse fixture implicitly for every test in its
    scope, never via a direct call token a text scan can see. Originally
    written for WIRE001 (T-1510); moved here (T-1651, `frob.gates._wire`
    imports it back rather than duplicating) so DEAD001 shares the exact
    same rescue -- DEAD001 was missing this exemption entirely and flagged
    5 of this repo's own autouse fixtures as dead code before this fix."""
    try:
        lines = (root / record.id.path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    start, end = record.span
    snippet = "\n".join(lines[start - 1 : end])
    return bool(_AUTOUSE_FIXTURE_RE.search(snippet))


# frob:ticket T-1652
_PYDANTIC_VALIDATOR_RE = re.compile(
    r"@(?:pydantic\.)?(?:field_validator|model_validator)\s*\(",
)


# frob:ticket T-1652
def _is_pydantic_validator(root: Path, record) -> bool:
    """True if `record`'s span opens with an `@field_validator(...)` or
    `@model_validator(...)` decorator (bare or `pydantic.`-qualified) --
    pydantic invokes a validator via its own decorator-registry dispatch
    at model-construction/field-assignment time, never via a call token
    this gate's package-scoped `build_reference_graph` scan (or any
    text-adjacent scan) can see, the identical dynamic-dispatch shape
    WIRE001's `_is_autouse_pytest_fixture` (T-1510) already rescues for
    pytest fixtures. Confirmed empirically (T-1651): 9 of this repo's own
    20 real (post-symref-fix) DEAD001 findings were exactly this shape --
    `AppConfig`/`TicketSpec`/`AcceptanceCriterion` field validators with
    zero call-graph callers by construction, not genuinely dead."""
    try:
        lines = (root / record.id.path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    start, end = record.span
    snippet = "\n".join(lines[start - 1 : end])
    return bool(_PYDANTIC_VALIDATOR_RE.search(snippet))


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


# frob:ticket T-1881
_NESTED_SCOPE_KINDS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _collect_returns_skip_nested(stmts: list[ast.stmt], out: list[ast.Return]) -> bool:
    """Collect every `ast.Return` reachable from `stmts` into `out`,
    recursing into control-flow statements (`If`/`Try`/`With`/`For`/
    `While`) but never crossing into a nested `FunctionDef`/
    `AsyncFunctionDef`/`ClassDef`/`Lambda` -- a `return` inside a nested
    `def` belongs to THAT function's own scope, not the one being
    analyzed. Returns `False` (poison) the instant a `Yield`/`YieldFrom`
    is seen anywhere in this scope's own statements (a generator's
    "return value" is not a plain call-return, and this narrow analysis
    has no business folding it) -- callers must discard the whole
    function on a poison, not merely the offending branch."""
    for stmt in stmts:
        if isinstance(stmt, _NESTED_SCOPE_KINDS):
            continue
        if isinstance(stmt, ast.Return):
            out.append(stmt)
            continue
        # Expression statements (a bare `yield` used as a statement) and
        # any other simple statement never contain a nested block to
        # recurse into, but MAY contain a `yield` expression directly.
        for expr_node in ast.walk(stmt) if not hasattr(stmt, "body") else ():
            if isinstance(expr_node, (ast.Yield, ast.YieldFrom)):
                return False
        for block in (
            getattr(stmt, "body", None),
            getattr(stmt, "orelse", None),
            getattr(stmt, "finalbody", None),
        ):
            if block and not _collect_returns_skip_nested(block, out):
                return False
        for handler in getattr(stmt, "handlers", None) or ():
            if not _collect_returns_skip_nested(handler.body, out):
                return False
    return True


def _constant_return_functions(tree: ast.Module) -> dict[str, object]:
    """Module-level, non-decorated function defs where EVERY `return`
    reachable in the function's own scope (recursing through `if`/`try`/
    `with`/loops, never into a nested `def`) evaluates to the SAME
    literal constant -- name -> that literal value. Broader than "body is
    textually one `return <literal>` statement": the real `_store_mode`
    shape after T-1552 stage 1 keeps an `if <cond>: return "v2"` guard
    ahead of a final `return "v2"`, still provably single-valued, but not
    a single top-level statement. No calls, no dataflow across a boundary
    -- purely "does this function's own return set collapse to one
    value" (day-scope per the ticket's acceptance criteria, not full
    interprocedural constant-propagation). A function with zero
    statically-constant returns, a MIXED return set, or a `yield`
    anywhere in its own scope is excluded (`None`/unconstrained is always
    the safe answer -- never guess)."""
    out: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.decorator_list:
            continue
        returns: list[ast.Return] = []
        if not _collect_returns_skip_nested(node.body, returns):
            continue
        if not returns:
            continue
        values = []
        ok = True
        for ret in returns:
            if not isinstance(ret.value, ast.Constant):
                ok = False
                break
            values.append(ret.value.value)
        if ok and values and all(v == values[0] for v in values):
            out[node.name] = values[0]
    return out


def _folded_bool(
    test: ast.expr,
    const_funcs: dict[str, object],
    locals_: dict[str, object],
    bool_locals: dict[str, bool] | None = None,
) -> bool | None:
    """Statically fold `test` to `True`/`False`. Two recognized shapes
    (T-1881 acceptance [1] -- "call site or one local-variable hop
    away"):

    1. A single `<producer>() == <literal>` (or `!=`) comparison where
       `<producer>` is either a direct call to a known constant-return
       function or a LOCAL VARIABLE bound to such a call one assignment
       earlier.
    2. A bare `Name` already bound in `bool_locals` -- the real repo's
       `v2_mode = _store_mode(root) == "v2"` shape, where the BOOLEAN
       (not the raw producer call) is the thing later reused directly as
       an `if`/ternary test, one further hop removed from shape 1.

    `None` if neither shape is recognized, which callers must treat as
    "cannot fold, do not touch this branch"."""
    if (
        bool_locals is not None
        and isinstance(test, ast.Name)
        and test.id in bool_locals
    ):
        return bool_locals[test.id]
    if not (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], (ast.Eq, ast.NotEq))
    ):
        return None
    left, right = test.left, test.comparators[0]
    if isinstance(right, ast.Constant) and not isinstance(left, ast.Constant):
        producer, literal = left, right.value
    elif isinstance(left, ast.Constant) and not isinstance(right, ast.Constant):
        producer, literal = right, left.value
    else:
        return None
    if isinstance(producer, ast.Call) and isinstance(producer.func, ast.Name) and (
        producer.func.id in const_funcs
    ):
        # Whatever arguments this call passes are irrelevant: every
        # `return` in the callee's own body already proved to fold to the
        # SAME literal regardless of parameters (`_constant_return_
        # functions` never reads a parameter to decide that), so the
        # call's actual argument expressions need no inspection here.
        produced = const_funcs[producer.func.id]
    elif isinstance(producer, ast.Name) and producer.id in locals_:
        produced = locals_[producer.id]
    else:
        return None
    equal = produced == literal
    return equal if isinstance(test.ops[0], ast.Eq) else not equal


def _stmt_span(stmts: list[ast.stmt]) -> tuple[int, int]:
    """1-indexed inclusive `(first_lineno, last_lineno)` covering every
    statement in `stmts`, using `end_lineno` where available (falls back
    to `lineno` for a single-line statement on interpreters that omit it,
    which none currently supported here do)."""
    first = min(s.lineno for s in stmts)
    last = max(getattr(s, "end_lineno", s.lineno) or s.lineno for s in stmts)
    return first, last


def _expr_span(node: ast.expr) -> tuple[int, int]:
    """`_stmt_span`'s expression-level twin, for a single `ast.expr` (a
    ternary's dead operand, which is not itself a statement)."""
    end = getattr(node, "end_lineno", node.lineno) or node.lineno
    return node.lineno, end


# frob:ticket T-1881
def _fold_ifexps_in_stmt(
    stmt: ast.stmt,
    const_funcs: dict[str, object],
    local: dict[str, object],
    bool_locals: dict[str, bool],
    dead_ranges: list[tuple[int, int]],
) -> None:
    """Fold a ternary (`ast.IfExp`) the same way `_walk_dead_ranges` folds
    an `if` STATEMENT -- the real repo's `_land_squash.py` denominator
    case is exactly this shape: `_squash_and_splice_ledger_v2(...) if
    v2_mode else _squash_and_splice_ledger(...)`, a single expression, not
    a statement `if`. Scans `stmt`'s own subexpressions (a bare
    `ast.walk`, so this also sees a ternary nested inside a nested
    function/lambda and folds it against the OUTER `local`/`bool_locals`
    maps -- imprecise in that rare case, but never in the
    false-accusation direction: it can only fold using bindings genuinely
    established earlier in the enclosing scope)."""
    for node in ast.walk(stmt):
        if not isinstance(node, ast.IfExp):
            continue
        folded = _folded_bool(node.test, const_funcs, local, bool_locals)
        if folded is True:
            dead_ranges.append(_expr_span(node.orelse))
        elif folded is False:
            dead_ranges.append(_expr_span(node.body))


_TERMINAL_STMT_KINDS = (ast.Return, ast.Raise, ast.Continue, ast.Break)


def _always_exits(stmts: list[ast.stmt]) -> bool:
    """True if `stmts`'s LAST statement unconditionally leaves the
    enclosing block (`return`/`raise`/`continue`/`break`) -- the
    guard-clause shape `_walk_dead_ranges` needs to fold `if <cond>:
    <...>; return X` followed by unindented fall-through code (no
    `else:` at all -- this repo's dominant idiom per T-1881's real
    denominator, e.g. `_store.py`'s `if _store_mode(root) == "v2":
    return _write_archive_v2(...)` followed by the v1 path at the same
    indentation). Deliberately shallow: only the textually LAST
    statement is checked, not a full CFG walk of every nested branch --
    day-scope, matching this module's other heuristics."""
    return bool(stmts) and isinstance(stmts[-1], _TERMINAL_STMT_KINDS)


def _walk_dead_ranges(
    stmts: list[ast.stmt],
    const_funcs: dict[str, object],
    locals_: dict[str, object],
    dead_ranges: list[tuple[int, int]],
) -> None:
    """Recursively fold `if`/`else` branches (AND the guard-clause
    fall-through shape `_always_exits` recognizes) in `stmts` in source
    order, threading a shallow `locals_` map (`name -> literal`, single
    assignment-hop, invalidated on any other assignment) and appending
    every provably-unreachable span to `dead_ranges`. Everything
    textually inside an already-dead branch (or after a folded-True
    guard clause) is dead by construction -- no further folding needed
    there; only the LIVE side of a resolved `if` is recursed into, so a
    nested fold still catches a second `if` layered inside the alive
    branch."""
    local = dict(locals_)
    bool_locals: dict[str, bool] = {}
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # A nested scope starts with no knowledge of the enclosing
            # scope's locals (shallow, intra-procedural only) but the
            # module-level `const_funcs` map still applies.
            _walk_dead_ranges(stmt.body, const_funcs, {}, dead_ranges)
            continue
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            target = stmt.targets[0].id
            value = stmt.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in const_funcs
            ):
                # Same "arguments don't matter" reasoning as `_folded_bool`.
                local[target] = const_funcs[value.func.id]
                bool_locals.pop(target, None)
            else:
                local.pop(target, None)
                # T-1881: `v2_mode = _store_mode(root) == "v2"` -- the
                # BOOLEAN result of a foldable comparison, reused bare in
                # a later `if`/ternary test (`_folded_bool`'s shape 2).
                folded_value = _folded_bool(value, const_funcs, local, bool_locals)
                if folded_value is None:
                    bool_locals.pop(target, None)
                else:
                    bool_locals[target] = folded_value
        _fold_ifexps_in_stmt(stmt, const_funcs, local, bool_locals, dead_ranges)
        if isinstance(stmt, ast.If):
            folded = _folded_bool(stmt.test, const_funcs, local, bool_locals)
            if folded is True:
                if stmt.orelse:
                    dead_ranges.append(_stmt_span(stmt.orelse))
                _walk_dead_ranges(stmt.body, const_funcs, local, dead_ranges)
                if not stmt.orelse and _always_exits(stmt.body):
                    rest = stmts[index + 1 :]
                    if rest:
                        dead_ranges.append(_stmt_span(rest))
                    return
                continue
            if folded is False:
                dead_ranges.append(_stmt_span(stmt.body))
                if stmt.orelse:
                    _walk_dead_ranges(stmt.orelse, const_funcs, local, dead_ranges)
                continue
            _walk_dead_ranges(stmt.body, const_funcs, dict(local), dead_ranges)
            if stmt.orelse:
                _walk_dead_ranges(stmt.orelse, const_funcs, dict(local), dead_ranges)


# frob:ticket T-1881
_MAX_TRANSITIVE_ROUNDS = 10


def _dead_only_names(root: Path, files: tuple[str, ...]) -> frozenset[str]:
    """T-1881: names whose EVERY `ast.Name` occurrence across `files`
    falls inside a provably-dead branch (`_walk_dead_ranges`) -- the
    override signal `dead_symbol_gate` applies on top of
    `build_reference_graph`'s purely-syntactic reachability, which
    cannot distinguish a call site sitting in an unreachable `else` arm
    from a live one.

    T-1881 evidence item (c) -- transitive propagation: a call site can
    sit in a DIFFERENT file than the one carrying the `_store_mode`-shaped
    fold, inside a function whose OWN only caller is itself fold-dead (the
    real repo's `_render_ledger`/`_splice_and_stage` shape -- called from
    `_land_git_ops.py`, which has no local fold of its own, but whose
    caller function is only ever invoked from a branch a DIFFERENT file's
    fold proved dead). Handled with a bounded fixed point: once a
    module-level function's short name is proven dead-only, its own
    ENTIRE body is folded into `dead_lines_by_file` for its own file (a
    dead function's call sites prove nothing about its callees' liveness
    either) and the name scan reruns; repeats until no new name is proven
    dead-only or `_MAX_TRANSITIVE_ROUNDS` is hit (this repo's own
    packages are tens of symbols -- a handful of rounds always reaches a
    fixed point in practice, the cap exists only as a hard stop against a
    pathological input, never observed to bind).

    Conservative in the same direction as this module's other heuristics:
    a name with even ONE live occurrence is left alone, never
    over-declared dead. Python-only, matching this gate's own file
    filter."""
    trees: dict[str, ast.Module] = {}
    def_spans_by_name: dict[str, list[tuple[str, int, int]]] = {}
    const_funcs: dict[str, object] = {}
    for path in files:
        if not path.endswith(".py"):
            continue
        try:
            source = (root / path).read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        trees[path] = tree
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                def_spans_by_name.setdefault(node.name, []).append(
                    (path, node.lineno, end)
                )
        # T-1881: collected PACKAGE-WIDE, not per-file -- the real
        # `_store_mode` shape is DEFINED in one file (`_store.py`) and
        # CALLED, after an `import`, from sibling files in the same
        # package (`_land_squash.py`'s `_store_mode(root) == "v2"`
        # ternary guard) -- a per-file-only `const_funcs` map would never
        # see the fold opportunity in any file that merely imports the
        # producer. Same name-based imprecision this whole substrate
        # already accepts elsewhere (two same-named producers in
        # different files would collide) -- not a new soundness gap.
        const_funcs.update(_constant_return_functions(tree))
    if not const_funcs:
        return frozenset()

    dead_lines_by_file: dict[str, set[int]] = {}
    any_fold = False
    for path, tree in trees.items():
        dead_ranges: list[tuple[int, int]] = []
        _walk_dead_ranges(tree.body, const_funcs, {}, dead_ranges)
        if not dead_ranges:
            continue
        any_fold = True
        lines = dead_lines_by_file.setdefault(path, set())
        for start, end in dead_ranges:
            lines.update(range(start, end + 1))
    if not any_fold:
        return frozenset()

    def _scan_names() -> frozenset[str]:
        """One name-occurrence pass over the current `dead_lines_by_file`
        state -- names whose every `ast.Name` Load occurrence across
        `trees` lands inside a dead line."""
        live_names: set[str] = set()
        dead_candidate_names: set[str] = set()
        for path, tree in trees.items():
            dead_lines = dead_lines_by_file.get(path, frozenset())
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.lineno in dead_lines:
                        dead_candidate_names.add(node.id)
                    else:
                        live_names.add(node.id)
        return frozenset(dead_candidate_names - live_names)

    dead_only = _scan_names()
    seen_dead_defs: set[str] = set()
    for _round in range(_MAX_TRANSITIVE_ROUNDS):
        newly_dead_defs = dead_only - seen_dead_defs
        if not newly_dead_defs:
            break
        grew = False
        for name in newly_dead_defs:
            for def_path, start, end in def_spans_by_name.get(name, ()):
                lines = dead_lines_by_file.setdefault(def_path, set())
                before = len(lines)
                lines.update(range(start, end + 1))
                grew = grew or len(lines) != before
        seen_dead_defs |= newly_dead_defs
        if not grew:
            break
        dead_only = _scan_names()
    return dead_only


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0422
# frob:ticket T-1881
# frob:tests \
# tests/test_gates.py::TestDeadSymbolGate.test_unwired_private_function_is_flagged
# frob:tests \
# tests/test_gates.py::TestDeadSymbolGate.test_called_private_helper_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_dunder_method_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_test_function_is_not_flagged
# frob:tests \
# tests/test_gates.py::TestDeadSymbolGate.test_tests_edge_target_is_not_flagged
# frob:enforces CHK-GATE-DEAD001
# frob:waive ARCH001 reason="the per-package reference-graph cache (called_by_package) \
# is built lazily inside the loop and keyed by the record being examined; splitting \
# the per-record body into a helper would require passing the mutable cache dict and \
# root/package derivation across a new boundary for no reduction in branching, the \
# same shape already accepted for this module's sibling gates"
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
    dead_only_by_package: dict[str, frozenset[str]] = {}
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
        if _is_pydantic_validator(root, record):
            continue
        if _is_autouse_pytest_fixture(root, record):
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
            # T-1881: a syntactic call token can still sit inside a branch
            # that constant-folding proves unreachable (the `_store_mode`
            # shape) -- `called` alone cannot tell live and dead call
            # sites apart. Only override when EVERY occurrence of this
            # symbol's own short name in the package is dead-only.
            dead_only = dead_only_by_package.get(package)
            if dead_only is None:
                files = _package_files(root, record.id.path)
                dead_only = _dead_only_names(root, files)
                dead_only_by_package[package] = dead_only
            if qualname.rsplit(".", 1)[-1] not in dead_only:
                continue
        violations.append(
            Violation(
                rule="DEAD001",
                severity=Severity.WARN,
                file=record.id.path,
                line=record.span[0],
                symref=symref,
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
