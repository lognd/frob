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
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from collections.abc import Sequence

from frob.gates._models import Severity, Violation
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
def _perf010_yaml_c_loader(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF010: `yaml.safe_load(...)`/`yaml.load(...)` called with no
    `CSafeLoader`/`CLoader` token anywhere in this symbol's own body --
    mined from `src/frob/tickets/_store.py`'s pre-T-1206 shape (every
    per-document `yaml.safe_load` call defaulted to the pure-python
    `SafeLoader`)."""
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
            return _violation(
                "PERF010",
                path,
                symbol.span[0],
                f"yaml.{tokens[i + 2]}(...) called with no C-accelerated "
                "loader token (CSafeLoader/CLoader) anywhere in "
                f"{symbol.qualname}",
            )
    return None


# frob:ticket T-1225
def _perf011_repo_scan_in_loop(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF011: a repo-scan API call (`xref`/`exports_consumers`/
    `iter_files`) that appears AFTER a `for`/`while` token in the
    flattened token stream -- the same coarse "loop token seen earlier in
    the stream" gate PERF001-004 already use (`_rules.py`'s own module
    docstring: loop-context is function-granularity, not true lexical
    nesting). Mined from `src/frob/gates/_debt_deprecated.py`'s pre-T-1207
    shape: a per-symbol `exports_consumers`+`xref` double full-repo scan
    inside a loop over every tracked symbol."""
    tokens = symbol.body_tokens
    n = len(tokens)
    seen_loop = False
    for i in range(n):
        if tokens[i] in _LOOP_TOKENS:
            seen_loop = True
            continue
        if not seen_loop:
            continue
        if tokens[i] in _REPO_SCAN_CALLEES and i + 1 < n and tokens[i + 1] == "(":
            return _violation(
                "PERF011",
                path,
                symbol.span[0],
                f"{tokens[i]}(...) (a full-repo scan API) is called inside "
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


# frob:ticket T-1225
def _perf014_finditer_in_nested_loop(symbol: RawSymbol, path: str) -> Violation | None:
    """PERF014: a `.finditer(...)` call preceded by THREE OR MORE `for`/
    `while` tokens in the flattened stream -- mined from
    `src/frob/gates/_secrets.py`'s pre-T-1211 shape (33 compiled patterns
    x one `finditer` call per PHYSICAL LINE: a pattern-list loop nested
    inside a per-line loop). The threshold is 3, not 2: the innermost
    `for match in pattern.finditer(...)` loop that directly consumes
    `finditer`'s own results always contributes one `for` token that
    lexically precedes the call -- the fixed one-loop-per-pattern shape
    (`for pattern in patterns: for match in pattern.finditer(text)`) has
    exactly 2 preceding `for` tokens (that consuming loop plus the
    pattern-list loop) and must stay silent; the pre-fix shape adds a
    THIRD, genuinely separate per-line loop wrapping both. Coarse
    count-based nesting check (this module's own docstring: false
    negatives accepted over exact lexical block tracking), matching
    `_rules.py`'s own PERF003 loop-count posture."""
    tokens = symbol.body_tokens
    for i, tok in enumerate(tokens):
        if tok != "finditer" or i + 1 >= len(tokens) or tokens[i + 1] != "(":
            continue
        preceding_loops = sum(1 for t in tokens[:i] if t in _LOOP_TOKENS)
        if preceding_loops >= 3:
            return _violation(
                "PERF014",
                path,
                symbol.span[0],
                f"finditer(...) is preceded by {preceding_loops} nested "
                f"loop(s) in {symbol.qualname} -- looks like a "
                "pattern-list loop nested inside a per-line loop",
            )
    return None


# frob:ticket T-1225
def _symbol_violations(symbol: RawSymbol, path: str) -> tuple[Violation, ...]:
    """Every PERF010/011/013/014 finding for one function/method symbol --
    each of the four checks called explicitly by name (not via a
    dispatch-table loop) so a plain text/call-graph scan of this module
    can see the real wiring (WIRE001's own call-shaped reachability
    scan, `frob.gates._wire._is_reached_outside_diff_tests`)."""
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
    perf014 = _perf014_finditer_in_nested_loop(symbol, path)
    if perf014 is not None:
        hits.append(perf014)
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
    non-Python files contribute nothing. Pure, consumed by
    `frob.perf.perf_rules`."""
    violations: list[Violation] = []
    for file in files:
        if file.language != "python":
            continue
        for symbol in file.symbols:
            violations.extend(_symbol_violations(symbol, file.path))
    _log.info(
        "hotpath_smell_violations: scanned %d file(s), %d violation(s)",
        len(files),
        len(violations),
    )
    return tuple(violations)
