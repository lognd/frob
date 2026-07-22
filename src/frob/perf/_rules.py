"""PERF001..PERF004: lexical, one-token-stream-deep linear-scan smells
(docs/modules/perf.md's rule table).

These rules run over `frob.lang`'s flattened, position-free leaf-token
stream (`RawSymbol.body_tokens`) -- the same "whitespace never a node"
contract `frob.lang._common._leaf_tokens` already gives every grammar. That
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

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.lang._models import ParsedFile, RawSymbol, SymbolKind
from frob.logging import get_logger
from frob.perf._recursion import recursion_rules
from frob.perf._redundancy import redundant_computation_violations

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

_OPENERS = frozenset({"(", "[", "{"})
_CLOSERS = frozenset({")", "]", "}"})

# T-0230: `body_tokens` is position-free by contract (module docstring) --
# these patterns drive a second, line-aware pass over the raw source text
# to recover the OFFENDING statement's real line, instead of always
# anchoring a finding at the enclosing symbol's `span[0]` (the `def`/`fn`
# line). The token stream still decides WHETHER a rule fires (unchanged);
# these patterns only decide WHERE to point the finding once it has.
_PERF002_LINE_PATTERN = re.compile(r"\.(?:index|count)\(")
_PERF004_SORT_CALL_PATTERN = re.compile(r"\bsorted\(|\.sort\(")
_PERF004_FOR_IN_SORTED_PATTERN = re.compile(r"\bfor\b.+\bin\s+sorted\(")
_EQ_PATTERN = re.compile(r"==")
_INCLUDES_PATTERN = re.compile(r"\.includes\(")
_INDEXOF_PATTERN = re.compile(r"\.indexOf\(")
_CONTAINS_PATTERN = re.compile(r"\.contains\(")


# frob:ticket T-0230
def _source_lines(path: str, span: tuple[int, int]) -> tuple[str, ...]:
    """Raw source lines covering `span` (1-based inclusive), re-read from
    `path` -- `()` if the file cannot be opened (moved/deleted since parse,
    or `path` not resolvable from the current working directory), in which
    case every caller below falls back to `span[0]`, the old enclosing-def
    anchor. `ParsedFile.path` is the same repo-relative/absolute string
    `frob.lang._display_path` already hands every other consumer, so this
    re-read is consistent with how the rest of the tool treats it."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ()
    start, end = span
    return tuple(text.splitlines())[start - 1 : end]


# frob:ticket T-0230
def _first_matching_line(
    lines: tuple[str, ...], span_start: int, patterns: Sequence[re.Pattern[str]]
) -> int:
    """1-based absolute line number of the first line in `lines` (offset
    from `span_start`) matching any of `patterns`, or `span_start` itself
    if `lines` is empty or nothing matches -- the safe fallback to the old
    anchor-at-`def` behavior."""
    for offset, line in enumerate(lines):
        if any(p.search(line) for p in patterns):
            return span_start + offset
    return span_start


# frob:ticket T-0230
def _perf001_line(
    tokens: tuple[str, ...], lines: tuple[str, ...], span_start: int
) -> int:
    """Line of the first `<x> in <list-name>` membership test, restricted
    to list-kind names (`_container_kinds`) and skipping `for ... in
    <name>:` loop-header lines, which share the same `in <name>` shape but
    are not a membership test."""
    names = [name for name, kind in _container_kinds(tokens).items() if kind == "list"]
    if not names:
        return span_start
    pattern = re.compile(r"\bin\s+(?:" + "|".join(re.escape(n) for n in names) + r")\b")
    for offset, line in enumerate(lines):
        if line.strip().startswith("for "):
            continue
        if pattern.search(line):
            return span_start + offset
    return span_start


# frob:ticket T-0230
def _perf004_line(lines: tuple[str, ...], span_start: int) -> int:
    """Line of the first `sorted(`/`.sort(` call that is not itself a
    `for ... in sorted(...):` loop-iterable header (excluded from firing in
    the first place by `_perf004_python`, and excluded here from line
    selection for the same reason)."""
    for offset, line in enumerate(lines):
        if _PERF004_SORT_CALL_PATTERN.search(
            line
        ) and not _PERF004_FOR_IN_SORTED_PATTERN.search(line):
            return span_start + offset
    return span_start


# frob:ticket T-0161
def _bracket_depths(tokens: tuple[str, ...]) -> tuple[int, ...]:
    """Per-token bracket-nesting depth (0 = statement level, outside any
    `(`/`[`/`{`).

    This is the fix for T-0161's headline false-positive class: a `for`
    inside a list/set/dict comprehension or a generator expression (e.g.
    `{x for x in y}`, `any(x == y for x in y)`, `sorted(x for x in y)`) sits
    at depth >= 1, while a real statement-level `for`/`while` loop header
    sits at depth 0. Every loop-context check below (`_loop_gate`,
    `_perf003`) consults this instead of "any 'for' token anywhere in the
    function," which is what made comprehensions and generator expressions
    lexically indistinguishable from real nested loops."""
    depths: list[int] = []
    depth = 0
    for tok in tokens:
        if tok in _OPENERS:
            depths.append(depth)
            depth += 1
        elif tok in _CLOSERS:
            depth = max(depth - 1, 0)
            depths.append(depth)
        else:
            depths.append(depth)
    return tuple(depths)


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
# frob:ticket T-0161
def _loop_gate(tokens: tuple[str, ...], depths: tuple[int, ...], upto: int) -> bool:
    """True if a statement-level (bracket depth 0) `for`/`while` keyword
    appears before index `upto` -- the function-level stand-in for
    "lexically inside a loop body". A `for`/`while` at depth >= 1 (a
    comprehension or generator-expression clause, e.g. `{x for x in y}`)
    is deliberately excluded: it is not a loop STATEMENT and never wraps
    the rest of the function the way a real `for`/`while` header does
    (T-0161's headline false-positive class)."""
    return any(
        t in _LOOP_TOKENS and depths[i] == 0 for i, t in enumerate(tokens[:upto])
    )


# frob:ticket T-0021
# frob:ticket T-0161
def _perf001_python(tokens: tuple[str, ...], depths: tuple[int, ...]) -> bool:
    """PERF001 (python): `x in <list-assigned-name>` inside a loop."""
    kinds = _container_kinds(tokens)
    for_ins = _for_clause_in_indices(tokens)
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok != "in" or i in for_ins or i + 1 >= n:
            continue
        if not _loop_gate(tokens, depths, i):
            continue
        rhs = tokens[i + 1]
        if kinds.get(rhs) == "list":
            return True
    return False


# frob:ticket T-0021
# frob:ticket T-0161
def _perf002_python(tokens: tuple[str, ...], depths: tuple[int, ...]) -> bool:
    """PERF002 (python): `.index(` or `.count(` call inside a loop."""
    n = len(tokens)
    for i in range(n - 2):
        if tokens[i] != "." or tokens[i + 2] != "(":
            continue
        if tokens[i + 1] not in ("index", "count"):
            continue
        if _loop_gate(tokens, depths, i):
            return True
    return False


# frob:ticket T-0021
# frob:ticket T-0161
def _header_colon_index(
    tokens: tuple[str, ...], depths: tuple[int, ...], start: int
) -> int | None:
    """Index of the `:` at depth 0 that closes the `for`/`while` header
    beginning at `start`, or None if the body is malformed/truncated."""
    n = len(tokens)
    i = start + 1
    while i < n:
        if tokens[i] == ":" and depths[i] == 0:
            return i
        i += 1
    return None


# frob:ticket T-0021
# frob:ticket T-0161
def _next_statement_loop(
    tokens: tuple[str, ...], depths: tuple[int, ...], start: int
) -> int | None:
    """Index of the next statement-level (depth 0) `for`/`while` keyword at
    or after `start`, or None. Unlike a strict "must be the very next
    token" adjacency check, this allows arbitrary intervening statements
    (an accumulator init, a guard, ...) between an outer loop's header
    colon and a real inner loop -- T-0161 round 2's fix for the reviewer-
    caught regression where `for x in a: y0 = 0; for y in b: if x == y:`
    (a common real-join shape: one setup statement before the inner loop)
    silently stopped firing under the original "colon immediately
    followed by inner `for`" adjacency rule."""
    n = len(tokens)
    for i in range(start, n):
        if tokens[i] in _LOOP_TOKENS and depths[i] == 0:
            return i
    return None


# frob:ticket T-0021
# frob:ticket T-0161
def _perf003(tokens: tuple[str, ...], depths: tuple[int, ...]) -> bool:
    """PERF003: a statement-level `for`/`while` loop whose body (allowing
    intervening statements, not just the literal next token -- see
    `_next_statement_loop`) contains a second statement-level loop, whose
    own body then contains an `==` comparison that actually involves the
    OUTER loop's bound variable -- the O(n*m) nested-equality-join shape.

    Relaxing the adjacency check to "anywhere later, allowing intervening
    statements" reopens the false-positive risk it was there to prevent
    (two sibling, non-nested loops are lexically indistinguishable from
    "outer loop, setup statement, inner loop" in this position-free token
    stream); see `_perf003_inner_equality_hit` for the added guard that
    closes it. `while` loops have no bound variable to check and fall back
    to "`==` anywhere in the inner body" -- an accepted, lower-volume gap.
    """
    n = len(tokens)
    for outer in range(n):
        if tokens[outer] not in _LOOP_TOKENS or depths[outer] != 0:
            continue
        colon = _header_colon_index(tokens, depths, outer)
        if colon is None or colon + 1 >= n:
            continue
        outer_var = _perf003_outer_var(tokens, outer, n)
        if _perf003_inner_equality_hit(tokens, depths, colon, outer_var):
            return True
    return False


def _perf003_outer_var(tokens: tuple[str, ...], outer: int, n: int) -> str | None:
    """The `for` loop's own bound variable name (the identifier right after
    `for`), or `None` for a `while` loop / malformed header."""
    if tokens[outer] == "for" and outer + 1 < n and tokens[outer + 1].isidentifier():
        return tokens[outer + 1]
    return None


def _perf003_inner_equality_hit(
    tokens: tuple[str, ...],
    depths: tuple[int, ...],
    outer_colon: int,
    outer_var: str | None,
) -> bool:
    """True if a nested statement-level loop after `outer_colon` has a body
    `==` that involves `outer_var` (or, when `outer_var` is None, any `==`
    at all -- the `while`-loop fallback described on `_perf003`).

    The outer loop's own bound variable must be one operand of the `==`
    found in the candidate inner loop's body -- real equality joins compare
    the outer element against something from the inner iteration
    (`if x == y`); an unrelated trailing `==` after two sibling loops
    (`assert len(out) == total`) almost never involves the outer loop's own
    loop variable by name. This is `_perf003`'s guard against the
    false-positive class its relaxed adjacency check reopened."""
    n = len(tokens)
    inner = _next_statement_loop(tokens, depths, outer_colon + 1)
    if inner is None:
        return False
    inner_colon = _header_colon_index(tokens, depths, inner)
    if inner_colon is None:
        return False
    for j in range(inner_colon + 1, n):
        if tokens[j] != "==":
            continue
        if outer_var is None:
            return True
        if _operand_names(tokens, j - 1, -1) & {outer_var} or _operand_names(
            tokens, j + 1, 1
        ) & {outer_var}:
            return True
    return False


# frob:ticket T-0161
# frob:ticket T-0246
def _operand_names(tokens: tuple[str, ...], start: int, step: int) -> frozenset[str]:
    """Identifier(s) making up the `==` operand adjacent to `tokens[start]`,
    walking outward in `step` direction (-1 = leftward, +1 = rightward).

    A bare name (`x == y`) is itself the operand. A subscript expression
    (`a[i - 1] == b[j - 1]`) is unwound one bracket pair so the index
    identifier (`i`) still counts -- this is what a real DP/edit-distance
    nested loop's join condition usually looks like, not a bare name
    comparison. A call expression (`f(x) == g(y)`) is unwound one level of
    call parens the same way (T-0246) -- a real nested join comparing
    DERIVED values (`f(x) == g(y)` with `x`/`y` the loop variables) is
    lexically identical to the subscript shape modulo the bracket
    character, so it gets the same one-level unwind, symmetric with the
    subscript handling above. Deliberately NOT extended to attribute access
    (`waiver.src == ...`): two sibling (non-nested) loops that happen to
    reuse the same loop variable name and each end in `<var>.attr ==
    something` (T-0161 round 2's reviewer-caught false-positive class,
    e.g. `for waiver in candidates: ... for waiver in candidates: ...`)
    would otherwise satisfy this check for both loops despite not being
    nested at all -- subscript/call unwinding both stay narrow on purpose,
    stopping at the first bracket/paren pair rather than descending
    further (e.g. `f(g(x)) == y` only unwinds to `g`/`x`'s outer call, not
    recursively into `g(x)`)."""
    n = len(tokens)
    if not (0 <= start < n):
        return frozenset()
    tok = tokens[start]
    if tok == "]":
        return _bracket_identifiers(tokens, start - 1, -1)
    if tok == "[":
        return _bracket_identifiers(tokens, start + 1, 1)
    if tok == ")":
        return _bracket_identifiers(tokens, start - 1, -1, brackets=("(", ")"))
    if tok == "(":
        return _bracket_identifiers(tokens, start + 1, 1, brackets=("(", ")"))
    if tok.isidentifier():
        return frozenset({tok})
    return frozenset()


# frob:ticket T-0246
def _bracket_identifiers(
    tokens: tuple[str, ...],
    start: int,
    step: int,
    brackets: tuple[str, str] = ("[", "]"),
) -> frozenset[str]:
    """Identifiers inside one `brackets` pair (default `[`/`]`, or `(`/`)`
    for T-0246's call-paren unwind), walking from `start` in `step`
    direction until the matching bracket closes (depth back to 0)."""
    n = len(tokens)
    open_b, close_b = brackets
    open_tok, close_tok = (open_b, close_b) if step == 1 else (close_b, open_b)
    depth = 1
    i = start
    names: set[str] = set()
    while 0 <= i < n and depth > 0:
        if tokens[i] == open_tok:
            depth += 1
        elif tokens[i] == close_tok:
            depth -= 1
            if depth == 0:
                break
        elif tokens[i].isidentifier():
            names.add(tokens[i])
        i += step
    return frozenset(names)


# frob:ticket T-0021
# frob:ticket T-0161
def _perf004_python(tokens: tuple[str, ...], depths: tuple[int, ...]) -> bool:
    """PERF004 (python): `sorted(` call or `.sort(` method call inside a
    loop, executed once per outer iteration -- excluding `sorted(...)`
    used as the loop's OWN iterable (`for x in sorted(data):`), which runs
    exactly once per call to the enclosing function, not once per
    iteration (T-0161's second named false-positive class)."""
    n = len(tokens)
    for_ins = _for_clause_in_indices(tokens)
    iterable_sorted = {
        k + 1 for k in for_ins if k + 1 < n and tokens[k + 1] == "sorted"
    }
    for i in range(n - 1):
        if (
            tokens[i] == "sorted"
            and tokens[i + 1] == "("
            and i not in iterable_sorted
            and _loop_gate(tokens, depths, i)
        ):
            return True
        if (
            i + 2 < n
            and tokens[i] == "."
            and tokens[i + 1] == "sort"
            and tokens[i + 2] == "("
            and _loop_gate(tokens, depths, i)
        ):
            return True
    return False


# frob:ticket T-0021
# frob:ticket T-0161
def _method_call_in_loop(
    tokens: tuple[str, ...], depths: tuple[int, ...], method: str
) -> bool:
    """True if `.<method>(` appears anywhere inside a loop -- the shared
    token-literal scan behind the TypeScript/Rust best-effort PERF rules."""
    n = len(tokens)
    for i in range(n - 2):
        if (
            tokens[i] == "."
            and tokens[i + 1] == method
            and tokens[i + 2] == "("
            and _loop_gate(tokens, depths, i)
        ):
            return True
    return False


# frob:ticket T-0021
def _perf001_best_effort(
    tokens: tuple[str, ...], depths: tuple[int, ...], language: str
) -> bool:
    """PERF001 (typescript/.includes, rust/Vec::contains): token-literal
    match plus the loop-token gate; no container-kind inference (the
    token stream carries no type info for these grammars)."""
    if language == "typescript":
        return _method_call_in_loop(tokens, depths, "includes")
    if language == "rust":
        return _method_call_in_loop(tokens, depths, "contains")
    return False


# frob:ticket T-0021
def _perf002_best_effort(
    tokens: tuple[str, ...], depths: tuple[int, ...], language: str
) -> bool:
    """PERF002 (typescript/.indexOf): token-literal match plus loop gate."""
    if language == "typescript":
        return _method_call_in_loop(tokens, depths, "indexOf")
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
# frob:ticket T-0230
def _python_violations(
    tokens: tuple[str, ...],
    depths: tuple[int, ...],
    path: str,
    span_start: int,
    lines: tuple[str, ...],
) -> list[Violation]:
    """PERF001/002/004 hits for a python function body (all four rules),
    each anchored at its own offending statement's line (T-0230), not the
    enclosing `def` line -- `span_start` is only the fallback when `lines`
    can't locate the real one."""
    hits: list[Violation] = []
    if _perf001_python(tokens, depths):
        line = _perf001_line(tokens, lines, span_start)
        hits.append(
            _violation("PERF001", path, line, "membership test over a list in a loop")
        )
    if _perf002_python(tokens, depths):
        line = _first_matching_line(lines, span_start, (_PERF002_LINE_PATTERN,))
        hits.append(
            _violation("PERF002", path, line, ".index()/.count() call in a loop")
        )
    if _perf004_python(tokens, depths):
        line = _perf004_line(lines, span_start)
        hits.append(
            _violation("PERF004", path, line, "sorted()/.sort() call in a loop")
        )
    return hits


# frob:ticket T-0021
# frob:ticket T-0230
def _best_effort_violations(
    tokens: tuple[str, ...],
    depths: tuple[int, ...],
    language: str,
    path: str,
    span_start: int,
    lines: tuple[str, ...],
) -> list[Violation]:
    """PERF001/002 hits for a non-python (typescript/rust) function body,
    each anchored at the actual `.includes(`/`.indexOf(`/`.contains(` call
    site (T-0230) rather than the enclosing function/fn line."""
    hits: list[Violation] = []
    if _perf001_best_effort(tokens, depths, language):
        pattern = _INCLUDES_PATTERN if language == "typescript" else _CONTAINS_PATTERN
        line = _first_matching_line(lines, span_start, (pattern,))
        hits.append(_violation("PERF001", path, line, "membership test in a loop"))
    if _perf002_best_effort(tokens, depths, language):
        line = _first_matching_line(lines, span_start, (_INDEXOF_PATTERN,))
        hits.append(_violation("PERF002", path, line, "linear index lookup in a loop"))
    return hits


# frob:ticket T-0021
# frob:ticket T-0230
def _symbol_violations(file: ParsedFile, symbol: RawSymbol) -> tuple[Violation, ...]:
    """Every PERF001..PERF004 hit inside one function/method symbol, each
    anchored at its own offending statement's real line (T-0230) via a
    line-aware re-read of the source (`_source_lines`), not always at the
    enclosing symbol's `span[0]` -- the position `body_tokens` alone cannot
    recover (module docstring)."""
    if symbol.kind not in _FUNCTION_KINDS:
        return ()
    tokens = symbol.body_tokens
    depths = _bracket_depths(tokens)
    span_start = symbol.span[0]
    lines = _source_lines(file.path, symbol.span)
    if file.language == "python":
        hits = _python_violations(tokens, depths, file.path, span_start, lines)
    else:
        hits = _best_effort_violations(
            tokens, depths, file.language, file.path, span_start, lines
        )
    if _perf003(tokens, depths):
        line = _first_matching_line(lines, span_start, (_EQ_PATTERN,))
        hits.append(
            _violation(
                "PERF003", file.path, line, "nested loops with an equality comparison"
            )
        )
    return tuple(hits)


# frob:doc docs/modules/perf.md#public-api
# frob:ticket T-0021
# frob:enforces CHK-GATE-PERF001
# frob:enforces CHK-GATE-PERF002
# frob:enforces CHK-GATE-PERF003
# frob:enforces CHK-GATE-PERF004
# frob:enforces CHK-GATE-PERF005
# frob:enforces CHK-GATE-PERF006
# frob:enforces CHK-GATE-PERF007
def perf_rules(
    snapshot: GraphSnapshot, files: Sequence[ParsedFile]
) -> tuple[Violation, ...]:
    """PERF001..PERF007 over every function/method symbol in `files`; pure,
    consumed by the policy/gates stage per docs/modules/perf.md's Integration
    points. PERF001-004 are self-contained per `ParsedFile` and never
    consult `snapshot`; PERF005/PERF006 (T-0290, recursion
    termination/depth) do -- `snapshot.edges` is where a reasoned
    `frob:invariant terminates reason="..." measure="..."` escape hatch
    lives (`frob.perf._recursion._termination_reasoned`). PERF007 (T-0413,
    the PERF META-GAP) is the one cross-FILE check here: a
    `frob.toml`-configured expensive call target invoked from 2+ distinct
    top-level symbols with no shared cache -- see
    `frob.perf._redundancy.redundant_computation_violations`."""
    violations: list[Violation] = []
    for file in files:
        for symbol in file.symbols:
            violations.extend(_symbol_violations(file, symbol))
    violations.extend(recursion_rules(snapshot, files))
    violations.extend(redundant_computation_violations(Path(snapshot.root), files))
    _log.info(
        "perf_rules: scanned %d file(s), %d violation(s)", len(files), len(violations)
    )
    return tuple(violations)
