"""PERF010..PERF014 (skipping PERF012, already taken by
`frob.perf._dup_spawn`): four lexical detectors mined directly from the
2026-07-29 hot-graph report's EPIC A root causes (T-1206/T-1207/T-1209/
T-1211's fixes) -- per repo convention, a perf root cause ships as both a
`.strata` obligation and a live PERF0xx lint rule, never as a fix-only
patch (T-1225). Each rule below is proven against a regression-corpus
fixture reproducing the EXACT pre-fix shape mined from the report so a
future regression re-introducing the pattern is caught statically:

- PERF010: `yaml.safe_load`/`yaml.load` without the C loader, in
  non-test code (mined from `src/frob/tickets/_store.py`'s pre-T-1206
  shape -- see that file's own `_yaml_loader` for the fixed form).
- PERF011: a repo-scan API (`xref`/`exports_consumers`/`iter_files`)
  called from inside a loop over symbols (mined from
  `src/frob/gates/_debt_deprecated.py`'s pre-T-1207 shape).
- PERF013: more than one `ast.walk(tree)` pass over the SAME tree
  argument within one function (mined from
  `src/frob/gates/_pii_structural/__init__.py`'s pre-T-1209 shape).
- PERF014: a `re.finditer` call nested inside a pattern-list loop that
  is itself nested inside a per-line loop (mined from
  `src/frob/gates/_secrets.py`'s pre-T-1211 shape).

All four are lexical, token-stream-deep checks over `RawSymbol.body_tokens`
-- the same coarse, formatting-insensitive, position-approximated posture
`_rules.py`'s own module docstring documents for PERF001-004 (false
negatives accepted, false positives minimized by requiring the specific
call/loop shape each rule was mined from, never a bare "loop present"
heuristic). Python-only: the report's own four root causes are all
Python-specific APIs (`yaml`, `ast`, `re.finditer`, this repo's own
`frob.xref`/`frob.exports`/`frob.testing._collect` surface), so there is
no cross-language best-effort tier here the way PERF001/002 have one.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from tree_sitter import Node

from frob.gates._models import Severity, Violation
from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["hotpath_smell_violations"]

# frob:ticket T-1225
_FUNCTION_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})
# frob:ticket T-1225
_LOOP_TOKENS = frozenset({"for", "while"})

# T-1206's own fix names both interchangeably: either C-accelerated loader
# (libyaml) counts as "already fast", so a bare presence check for either
# token anywhere in the symbol's own body is enough -- same "textual,
# conservative" posture `_redundancy._is_already_cached` documents for its
# own decorator-marker scan.
# frob:ticket T-1225
_C_LOADER_TOKENS = frozenset({"CSafeLoader", "CLoader"})
# frob:ticket T-1225
_YAML_LOAD_CALLEES = frozenset({"safe_load", "load"})

# T-1207's mined root cause: a full-repo scan API invoked once PER SYMBOL
# inside a loop, instead of once, hoisted outside it.
# frob:ticket T-1225
_REPO_SCAN_CALLEES = frozenset({"xref", "exports_consumers", "iter_files"})

# frob:ticket T-1225
_REMEDY = {
    "PERF010": (
        "pass Loader=yaml.CSafeLoader (or yaml.CLoader) explicitly -- the "
        "default PyYAML loader is the pure-python SafeLoader, orders of "
        "magnitude slower per document (T-1206)"
    ),
    "PERF011": (
        "hoist the repo-scan call (xref/exports_consumers/iter_files) "
        "outside the loop and index its result once, instead of re-running "
        "a full-repo scan per symbol (T-1207)"
    ),
    "PERF013": (
        "build one ast.walk(tree) index and pass it to every sub-scan, "
        "instead of each sub-scan re-walking the same tree (T-1209)"
    ),
    "PERF014": (
        "swap the loop nesting: one finditer() call over the whole text "
        "per pattern, not one per pattern per line (T-1211)"
    ),
}


# frob:ticket T-1225
def _violation(rule: str, path: str, line: int, detail: str) -> Violation:
    """One `Violation` in this module's shared shape -- WARN-tier (same
    disposition as PERF008/PERF012, `_loop_effects`/`_dup_spawn`'s own
    precedent: these are lexical smells with a real escape hatch
    (`frob:waive`), not proven-unsafe control flow the way PERF005/006
    are)."""
    return Violation(
        rule=rule,
        severity=Severity.WARN,
        file=path,
        line=line,
        message=f"{rule}: {detail} -- {_REMEDY[rule]}",
    )


# frob:ticket T-1225
def _is_test_path(path: str) -> bool:
    """Whether `path` is test code -- PERF010's own scope guard (this
    module's docstring: "in non-test code"), since test fixtures
    legitimately construct throwaway YAML documents where load speed
    never matters."""
    return "/tests/" in f"/{path}" or path.startswith("tests/")


# frob:ticket T-1225
def _has_loader_indirection(tokens: Sequence[str]) -> bool:
    """Whether `tokens` (a symbol's own body tokens) contains a `Loader=
    <helper>(...)` keyword argument delegating loader selection to a
    named helper, e.g. `Loader=_yaml_loader()`/`Loader=_tickets_yaml_
    loader()` -- the exact T-1206 fixed shape in `frob.tickets._store`/
    `frob.gates.__init__` (`_yaml_loader`/`_tickets_yaml_loader`, both
    already resolving to `yaml.CSafeLoader` when available). PERF010's
    original bare `CSafeLoader`/`CLoader`-token scan false-positived on
    both: it can only ever see a LITERAL loader-class token in the
    calling symbol's own body, never through a helper call boundary, so
    the repo's own established C-loader-selection convention (a small
    `*_loader()` factory, reused across every per-document parse site
    instead of repeating the CSafeLoader-availability probe at each call)
    permanently misread as "no C loader anywhere" (T-1420-adjacent
    finding). Any identifier containing "loader" (case-insensitive)
    immediately followed by a call is trusted as a deliberate loader
    -selection indirection -- the same naming convention this repo's own
    fix already established -- rather than requiring cross-symbol body
    inspection this lexical, single-symbol-scoped rule has no access to."""
    n = len(tokens)
    for i in range(n - 2):
        if (
            tokens[i] == "Loader"
            and tokens[i + 1] == "="
            and "loader" in tokens[i + 2].lower()
            and i + 3 < n
            and tokens[i + 3] == "("
        ):
            return True
    return False


# frob:ticket T-1225
def _perf010_yaml_c_loader(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF010: `yaml.safe_load(...)`/`yaml.load(...)` called with no
    `CSafeLoader`/`CLoader` token, and no `Loader=<helper>()` indirection
    to one (`_has_loader_indirection`), anywhere in this symbol's own
    body -- mined from `src/frob/tickets/_store.py`'s pre-T-1206 shape
    (every per-document `yaml.safe_load` call defaulted to the pure-
    python `SafeLoader`)."""
    if _is_test_path(path):
        return None
    tokens = symbol.body_tokens
    n = len(tokens)
    for i in range(n - 3):
        if (
            tokens[i] == "yaml"
            and tokens[i + 1] == "."
            and tokens[i + 2] in _YAML_LOAD_CALLEES
            and tokens[i + 3] == "("
        ):
            if any(t in _C_LOADER_TOKENS for t in tokens):
                continue
            if _has_loader_indirection(tokens):
                continue
            return _violation(
                "PERF010",
                path,
                symbol.span[0],
                f"yaml.{tokens[i + 2]}(...) called with no C-accelerated "
                "loader token (CSafeLoader/CLoader) anywhere in "
                f"{symbol.qualname}",
            )
    return None


# frob:ticket T-1647
_OPEN_BRACKETS = frozenset({"(", "[", "{"})
# frob:ticket T-1647
_CLOSE_BRACKETS = frozenset({")", "]", "}"})


# T-1647: PERF011 used to flag a repo-scan call the instant ANY for/while
# token appeared earlier in the flattened stream. An audit of every live
# PERF011 finding on main found this systematically misfired on
# `for x in <repo-scan-call>(...):` and its comprehension/genexpr
# equivalents -- that call is the loop's own ITERABLE expression,
# evaluated exactly ONCE to build the iterator, never "once per
# iteration" the way the mined T-1207 shape (a call inside the loop
# BODY) is. 22 of 31 findings were exactly this shape, including one
# where the "earlier loop" was an unrelated genexpr's own for-clause
# with no relation to the later, un-looped call it caused to misfire.
# See `_perf011_repo_scan_in_loop`'s own docstring below for the fix and
# its one disclosed residual gap (sibling, not nested, loops).
# frob:ticket T-1225
# frob:ticket T-1647
def _perf011_repo_scan_in_loop(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF011: a repo-scan API call (`xref`/`exports_consumers`/
    `iter_files`) called from inside a loop over symbols -- mined from
    `src/frob/gates/_debt_deprecated.py`'s pre-T-1207 shape. Tracks
    bracket depth and each depth-0 `for`/`while`'s own header span: a
    loop token INSIDE a bracket (a comprehension/genexpr's own for-clause)
    never sets loop-context, and a repo-scan call inside the FIRST depth-0
    loop's own header is exempted (a single iterator-building evaluation,
    not a repeat) -- see this module's own T-1647 comment above for the
    full rationale and its one disclosed gap."""
    tokens = symbol.body_tokens
    n = len(tokens)
    seen_loop = False
    depth = 0
    header_open = False
    header_is_first_loop = False
    for i in range(n):
        tok = tokens[i]
        if tok in _OPEN_BRACKETS:
            depth += 1
        elif tok in _CLOSE_BRACKETS:
            depth = max(0, depth - 1)

        if tok in _LOOP_TOKENS and depth == 0:
            header_is_first_loop = not seen_loop
            seen_loop = True
            header_open = True
            continue

        if header_open and tok == ":" and depth == 0:
            header_open = False
            continue

        if not seen_loop:
            continue

        if tok in _REPO_SCAN_CALLEES and i + 1 < n and tokens[i + 1] == "(":
            if header_open and header_is_first_loop:
                # This call IS the enclosing for/while's own iterable
                # expression, and that loop is the first (and so far only)
                # loop-context seen -- it runs exactly once, not per
                # iteration of anything. Not a violation (T-1647).
                continue
            return _violation(
                "PERF011",
                path,
                symbol.span[0],
                f"{tok}(...) (a full-repo scan API) is called inside "
                f"a loop in {symbol.qualname}",
            )
    return None


# frob:ticket T-1225
def _perf013_repeated_ast_walk(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF013: two or more `ast.walk(<same-arg>)` calls within one
    function -- mined from `src/frob/gates/_pii_structural/__init__.py`'s
    pre-T-1209 shape (each sub-scan independently walked the same parsed
    tree). The "same tree" half of the rule's own name is checked
    textually: the single token immediately inside the `walk(...)` call's
    parens must match across every hit, so `ast.walk(a)` followed by
    `ast.walk(b)` (two genuinely different trees) does not fire."""
    tokens = symbol.body_tokens
    n = len(tokens)
    walk_args: list[str] = []
    for i in range(n - 4):
        if (
            tokens[i] == "ast"
            and tokens[i + 1] == "."
            and tokens[i + 2] == "walk"
            and tokens[i + 3] == "("
        ):
            # Best-effort single-token argument capture (the common case:
            # a bare name, e.g. `ast.walk(tree)`) -- a multi-token
            # argument expression is intentionally not attributed as "the
            # same tree" (conservative: no false positive from two
            # differently-shaped call expressions that happen to both
            # start similarly).
            arg = tokens[i + 4] if i + 4 < n else ""
            walk_args.append(arg)
    if len(walk_args) < 2:
        return None
    seen: set[str] = set()
    for arg in walk_args:
        if arg and arg in seen:
            return _violation(
                "PERF013",
                path,
                symbol.span[0],
                f"ast.walk({arg}) is called more than once over the same "
                f"argument within {symbol.qualname}",
            )
        seen.add(arg)
    return None


# T-1649: PERF014 used to fire the instant THREE OR MORE for/while tokens
# appeared ANYWHERE earlier in the flattened token stream -- the same
# flaw T-1647 found and fixed in PERF011 (no way to tell a genuinely
# nested loop from an earlier, already-CLOSED sibling loop, since a flat
# token stream carries no block/indent structure). Auditing every live
# finding found the identical failure class here: `src/frob/gates/
# _docptr.py::_prose_tokens` (a listcomp's own `for` plus a first,
# single-level finditer loop, both SEQUENTIAL and preceding a second,
# genuinely-nested finditer) and `src/frob/gates/_refs.py::
# _python_import_targets` (two SEQUENTIAL top-level for-loops, each with
# its own single level of real nesting) both misfired this way.
#
# Fixed by dropping the token-stream heuristic entirely and re-parsing
# the file's real tree-sitter AST (the same substrate `frob.perf.
# _loop_effects._iter_loop_call_sites` already uses for PERF008, in this
# same package) to compute each `.finditer(...)` call's REAL ancestor
# loop-nesting depth -- how many `for_statement`/`while_statement` nodes'
# own BODY (not header/iterable) actually encloses the call, tracked via
# a depth-tagged pre-order stack walk. This structurally cannot conflate
# a sibling with a nested loop (a sibling loop is simply not an ancestor
# at all) and automatically excludes comprehension/genexpr `for`-clauses
# (they parse as `for_in_clause` inside `list_comprehension`/`generator_
# expression`, never `for_statement`, so they were never eligible to
# begin with -- no separate bracket-depth guard needed, unlike PERF011's
# token-stream fix, because the AST already carries that distinction).
#
# frob:ticket T-1649
_AST_LOOP_KINDS = frozenset({"for_statement", "while_statement"})


# frob:ticket T-1649
def _iter_calls_with_loop_depth(root: Node) -> list[tuple[Node, int]]:
    """Every `call` node under `root` paired with the count of real
    for/while loop ancestors whose BODY (not header/iterable expression)
    encloses it. A loop's own iterable expression -- e.g. the
    `pattern.finditer(text)` in `for match in pattern.finditer(text):` --
    is not part of that loop's body, so a call used to build a loop's own
    iterator is attributed to whatever loops enclose the `for`/`while`
    statement ITSELF, never to the loop that call's return value feeds
    (the same "this call IS the loop's own iterable, not a repeat"
    exemption `_perf011_repo_scan_in_loop`'s T-1647 fix carries, derived
    here for free from real AST containment instead of a header-span
    token scan)."""
    hits: list[tuple[Node, int]] = []
    stack: list[tuple[Node, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node.type in _AST_LOOP_KINDS:
            body = _child_by_field(node, "body")
            for child in node.children:
                # See `_iter_loop_call_sites`'s own note in _loop_effects.py:
                # tree-sitter Node wrappers are not identity-stable, `==`
                # compares the underlying node correctly.
                child_depth = depth + 1 if child == body else depth
                stack.append((child, child_depth))
            continue
        if node.type == "call":
            hits.append((node, depth))
        # frob:waive PERF003 reason="stack-based AST tree walk, one pass over nodes, not a cross join"  # noqa: E501
        stack.extend((child, depth) for child in node.children)
    return hits


# frob:ticket T-1649
def _is_finditer_call(call_node: Node) -> bool:
    """True if `call_node`'s callee is a bare or dotted `finditer` --
    `pattern.finditer(...)`/`re.compile(...).finditer(...)` (an
    `attribute` function expression) or a locally-bound bare `finditer`
    (an `identifier` function expression, e.g. `finditer = pat.finditer;
    finditer(text)`)."""
    func = _child_by_field(call_node, "function")
    if func is None:
        return False
    if func.type == "attribute":
        attr = _child_by_field(func, "attribute")
        return attr is not None and _node_text(attr) == "finditer"
    if func.type == "identifier":
        return _node_text(func) == "finditer"
    return False


# T-1649's own threshold: depth 0 or 1 is the FIXED, desired shape (`for
# pattern in patterns: for match in pattern.finditer(text):` -- the
# consuming `for match in ...` loop's own iterable expression contributes
# no depth per `_iter_calls_with_loop_depth`'s own exemption, so this
# shape measures depth 1, the pattern-list loop's body containment
# alone); depth >= 2 means the call sits inside a genuinely nested loop
# body two or more real levels deep, the mined pre-T-1211
# pattern-list-inside-per-line shape (or its structural equivalent, e.g.
# a per-directory x per-file x per-line walk calling `.finditer(line)`
# once per physical line three real levels deep).
# frob:ticket T-1649
_PERF014_NESTED_DEPTH_THRESHOLD = 2


# frob:ticket T-1649
def _perf014_ast_violations(path: str) -> list[Violation]:
    """PERF014, file-level (T-1649 rewrite -- see the `_AST_LOOP_KINDS`
    comment above for the full rationale): every `.finditer(...)` call
    site in `path` whose real AST loop-nesting depth
    (`_iter_calls_with_loop_depth`) is `>= _PERF014_NESTED_DEPTH_
    THRESHOLD`. `[]` if `path` cannot be re-parsed (moved/deleted since
    the original parse -- `frob.lang.raw_tree`'s own Result contract) or
    is not python (this module's docstring: PERF010/011/013/014 are all
    Python-only)."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return []
    tree, _source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    for call_node, depth in _iter_calls_with_loop_depth(tree.root_node):
        if depth < _PERF014_NESTED_DEPTH_THRESHOLD or not _is_finditer_call(call_node):
            continue
        line = call_node.start_point[0] + 1
        violations.append(
            _violation(
                "PERF014",
                path,
                line,
                f"finditer(...) is nested {depth} real loop level(s) deep "
                "-- looks like a pattern-list loop nested inside a "
                "per-line loop",
            )
        )
    return violations


# frob:ticket T-1225
def _symbol_violations(symbol: RawSymbol, path: str) -> tuple[Violation, ...]:
    """Every PERF010/011/013 finding for one function/method symbol -- each
    check called explicitly by name (not via a dispatch-table loop) so a
    plain text/call-graph scan of this module can see the real wiring
    (WIRE001's own call-shaped reachability scan, `frob.gates._wire.
    _is_reached_outside_diff_tests`). PERF014 (T-1649) is no longer a
    per-symbol token-stream check -- see `_perf014_ast_violations` and
    `hotpath_smell_violations`'s own per-file AST pass below."""
    if symbol.kind not in _FUNCTION_KINDS:
        return ()
    hits: list[Violation] = []
    perf010 = _perf010_yaml_c_loader(symbol, path)
    if perf010 is not None:
        hits.append(perf010)
    perf011 = _perf011_repo_scan_in_loop(symbol, path)
    if perf011 is not None:
        hits.append(perf011)
    perf013 = _perf013_repeated_ast_walk(symbol, path)
    if perf013 is not None:
        hits.append(perf013)
    return tuple(hits)


# frob:doc docs/modules/perf.md#public-api
# frob:ticket T-1225
# frob:enforces CHK-GATE-PERF010
# frob:enforces CHK-GATE-PERF011
# frob:enforces CHK-GATE-PERF013
# frob:enforces CHK-GATE-PERF014
# frob:tests tests/unit/perf/test_hotpath_smells.py::TestHotpathSmellsWiredIntoPerfRules.test_perf_rules_includes_perf010_finding kind="unit"  # noqa: E501
def hotpath_smell_violations(files: Sequence[ParsedFile]) -> tuple[Violation, ...]:
    """PERF010/011/013/014 over every Python function/method symbol in
    `files` -- the four EPIC A hot-graph root-cause detectors this
    module's own docstring names. Python-only (see module docstring);
    non-Python files contribute nothing. PERF014 (T-1649) runs as one
    per-file AST pass (`_perf014_ast_violations`) rather than per-symbol
    token scan, since real loop-nesting depth needs actual tree
    containment, not a flat token count -- see that function's own
    docstring. Pure, consumed by `frob.perf.perf_rules`."""
    violations: list[Violation] = []
    for file in files:
        if file.language != "python":
            continue
        for symbol in file.symbols:
            violations.extend(_symbol_violations(symbol, file.path))
        violations.extend(_perf014_ast_violations(file.path))
    _log.info(
        "hotpath_smell_violations: scanned %d file(s), %d violation(s)",
        len(files),
        len(violations),
    )
    return tuple(violations)
