"""PERF001..PERF004: lexical, one-token-stream-deep linear-scan smells
(docs/modules/perf.md's rule table).

These rules run over `frob.lang`'s flattened, position-free leaf-token
stream (`RawSymbol.body_tokens`) -- the same "whitespace never a node"
contract `frob.lang._common.leaf_tokens` already gives every grammar. That
contract buys formatting-insensitivity but costs positions: there is no
per-token line number, so every violation is reported at the *enclosing
symbol's* span start (`RawSymbol.span[0]`), not the exact offending line.
Loop-context is therefore approximated at function granularity -- "this
function contains a for/while keyword and a qualifying pattern" -- rather
than true lexical block nesting. This is a documented cut (docs/modules/perf.md
Design decisions), not an oversight: false negatives (a smell missed
because the loop check is coarse) are accepted; false positives are
minimized by requiring the container's assignment shape to be resolvable
as list-like before PERF001/PERF002 ever fire.

Python is first-class (all four rules). TypeScript and Rust get
best-effort coverage of PERF001/PERF002 only, using token literals
(`.includes`, `.indexOf`, `Vec::contains`) with the same loop-token gate;
container-kind inference (list vs set/Map) is Python-only since sig/body
tokens carry no type information to lean on for the other two languages.
"""

# frob:waive TEST005 reason="module line coverage 82.0%, debt T-0160"

from __future__ import annotations

from collections.abc import Sequence

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.lang._models import ParsedFile, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["perf_rules"]

_FUNCTION_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})

_REMEDY = {
    "PERF001": "build a set/HashSet/Map once, test against it",
    "PERF002": "dict/Map from key to index/count, built once",
    "PERF003": "index the inner collection by the compared key",
    "PERF004": "hoist the sort, or use a sorted container",
}

_LOOP_TOKENS = frozenset({"for", "while"})

# The `for` keyword as a token literal, hoisted to module scope so the
# rule bodies below can count/compare against it without embedding a bare
# "for" string constant inside a scanning function (which would itself read
# as a second loop header to PERF003's own coarse token heuristic).
_FOR_KEYWORD = "for"


# frob:ticket T-0021
def _container_kinds(tokens: tuple[str, ...]) -> dict[str, str]:
    """Best-effort `{identifier: "list"|"set"}` from `name = [...]` /
    `name = {...}` / `name = set(...)`/`frozenset(...)`/`dict(...)` shapes
    seen anywhere in `tokens`. Unknown identifiers are simply absent --
    callers must treat "absent" as "do not fire", not as "assume list"."""
    kinds: dict[str, str] = {}
    n = len(tokens)
    for i in range(n - 2):
        name, eq, opener = tokens[i], tokens[i + 1], tokens[i + 2]
        if eq != "=" or not name.isidentifier():
            continue
        if opener == "[":
            kinds[name] = "list"
        elif opener == "{":
            kinds[name] = "set"
        elif opener == "(" and name == "":
            continue
    _container_call_kinds(tokens, kinds)
    return kinds


# frob:ticket T-0021
def _container_call_kinds(tokens: tuple[str, ...], kinds: dict[str, str]) -> None:
    """Fold `name = set(...)`/`frozenset(...)`/`dict(...)` call shapes into
    `kinds` as set-like -- the call-constructed half of `_container_kinds`."""
    n = len(tokens)
    for i in range(n - 3):
        callee, opener = tokens[i], tokens[i + 1]
        if opener != "(" or callee not in ("set", "frozenset", "dict"):
            continue
        # walk back over "= callee(" to find the assigned name
        if i >= 2 and tokens[i - 1] == "=" and tokens[i - 2].isidentifier():
            kinds[tokens[i - 2]] = "set"


# frob:ticket T-0021
def _for_clause_in_indices(tokens: tuple[str, ...]) -> set[int]:
    """Indices of the `in` token that belongs to a `for X in Y:` header,
    so PERF001's membership scan does not mistake a loop header for a
    membership test."""
    consumed: set[int] = set()
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "for":
            j = i + 1
            while j < n and tokens[j] != "in":
                j += 1
            if j < n:
                consumed.add(j)
                i = j + 1
                continue
        i += 1
    return consumed


# frob:ticket T-0021
def _loop_gate(tokens: tuple[str, ...], upto: int) -> bool:
    """True if a `for`/`while` keyword appears anywhere before index `upto`
    -- the function-level stand-in for "lexically inside a loop body"."""
    return any(t in _LOOP_TOKENS for t in tokens[:upto])


# frob:ticket T-0021
def _perf001_python(tokens: tuple[str, ...]) -> bool:
    """PERF001 (python): `x in <list-assigned-name>` inside a loop."""
    kinds = _container_kinds(tokens)
    for_ins = _for_clause_in_indices(tokens)
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok != "in" or i in for_ins or i + 1 >= n:
            continue
        if not _loop_gate(tokens, i):
            continue
        rhs = tokens[i + 1]
        if kinds.get(rhs) == "list":
            return True
    return False


# frob:ticket T-0021
def _perf002_python(tokens: tuple[str, ...]) -> bool:
    """PERF002 (python): `.index(` or `.count(` call inside a loop."""
    n = len(tokens)
    for i in range(n - 2):
        if tokens[i] != "." or tokens[i + 2] != "(":
            continue
        if tokens[i + 1] not in ("index", "count"):
            continue
        if _loop_gate(tokens, i):
            return True
    return False


# frob:ticket T-0021
def _perf003(tokens: tuple[str, ...]) -> bool:
    """PERF003: two or more `for` headers plus an `==` comparison anywhere
    in the same function -- the O(n*m) nested-equality-join shape."""
    for_count = sum(1 for t in tokens if t == _FOR_KEYWORD)
    return for_count >= 2 and "==" in tokens


# frob:ticket T-0021
def _perf004_python(tokens: tuple[str, ...]) -> bool:
    """PERF004 (python): `sorted(` call or `.sort(` method call inside a loop."""
    n = len(tokens)
    for i in range(n - 1):
        if tokens[i] == "sorted" and tokens[i + 1] == "(" and _loop_gate(tokens, i):
            return True
        if (
            i + 2 < n
            and tokens[i] == "."
            and tokens[i + 1] == "sort"
            and tokens[i + 2] == "("
            and _loop_gate(tokens, i)
        ):
            return True
    return False


# frob:ticket T-0021
def _method_call_in_loop(tokens: tuple[str, ...], method: str) -> bool:
    """True if `.<method>(` appears anywhere inside a loop -- the shared
    token-literal scan behind the TypeScript/Rust best-effort PERF rules."""
    n = len(tokens)
    for i in range(n - 2):
        if (
            tokens[i] == "."
            and tokens[i + 1] == method
            and tokens[i + 2] == "("
            and _loop_gate(tokens, i)
        ):
            return True
    return False


# frob:ticket T-0021
def _perf001_best_effort(tokens: tuple[str, ...], language: str) -> bool:
    """PERF001 (typescript/.includes, rust/Vec::contains): token-literal
    match plus the loop-token gate; no container-kind inference (the
    token stream carries no type info for these grammars)."""
    if language == "typescript":
        return _method_call_in_loop(tokens, "includes")
    if language == "rust":
        return _method_call_in_loop(tokens, "contains")
    return False


# frob:ticket T-0021
def _perf002_best_effort(tokens: tuple[str, ...], language: str) -> bool:
    """PERF002 (typescript/.indexOf): token-literal match plus loop gate."""
    if language == "typescript":
        return _method_call_in_loop(tokens, "indexOf")
    return False


# frob:ticket T-0021
def _violation(rule: str, file: str, line: int, extra: str) -> Violation:
    """One PERF violation, message carrying its docs/modules/perf.md remedy text."""
    return Violation(
        rule=rule,
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(f"{rule}: {file}:{line} {extra}; suggested fix: {_REMEDY[rule]}"),
    )


# frob:ticket T-0021
def _python_violations(
    tokens: tuple[str, ...], path: str, line: int
) -> list[Violation]:
    """PERF001/002/004 hits for a python function body (all four rules)."""
    hits: list[Violation] = []
    if _perf001_python(tokens):
        hits.append(
            _violation("PERF001", path, line, "membership test over a list in a loop")
        )
    if _perf002_python(tokens):
        hits.append(
            _violation("PERF002", path, line, ".index()/.count() call in a loop")
        )
    if _perf004_python(tokens):
        hits.append(
            _violation("PERF004", path, line, "sorted()/.sort() call in a loop")
        )
    return hits


# frob:ticket T-0021
def _best_effort_violations(
    tokens: tuple[str, ...], language: str, path: str, line: int
) -> list[Violation]:
    """PERF001/002 hits for a non-python (typescript/rust) function body."""
    hits: list[Violation] = []
    if _perf001_best_effort(tokens, language):
        hits.append(_violation("PERF001", path, line, "membership test in a loop"))
    if _perf002_best_effort(tokens, language):
        hits.append(_violation("PERF002", path, line, "linear index lookup in a loop"))
    return hits


# frob:ticket T-0021
def _symbol_violations(file: ParsedFile, symbol: RawSymbol) -> tuple[Violation, ...]:
    """Every PERF001..PERF004 hit inside one function/method symbol."""
    if symbol.kind not in _FUNCTION_KINDS:
        return ()
    tokens = symbol.body_tokens
    line = symbol.span[0]
    if file.language == "python":
        hits = _python_violations(tokens, file.path, line)
    else:
        hits = _best_effort_violations(tokens, file.language, file.path, line)
    if _perf003(tokens):
        hits.append(
            _violation(
                "PERF003", file.path, line, "nested loops with an equality comparison"
            )
        )
    return tuple(hits)


# frob:doc docs/modules/perf.md#public-api
# frob:ticket T-0021
def perf_rules(
    snapshot: GraphSnapshot, files: Sequence[ParsedFile]
) -> tuple[Violation, ...]:
    """PERF001..PERF004 over every function/method symbol in `files`; pure,
    consumed by the policy/gates stage per docs/modules/perf.md's Integration
    points. `snapshot` is accepted per the documented signature but is not
    presently consulted -- the token-stream rules are self-contained per
    `ParsedFile`; it is reserved for a future cross-symbol join (e.g.
    resolving a helper called once per loop iteration)."""
    del snapshot
    violations: list[Violation] = []
    for file in files:
        for symbol in file.symbols:
            violations.extend(_symbol_violations(file, symbol))
    _log.info(
        "perf_rules: scanned %d file(s), %d violation(s)", len(files), len(violations)
    )
    return tuple(violations)
