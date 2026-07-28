# frob:ticket T-0160
"""Branch-coverage tests for `frob.perf._rules`'s internals -- the
TypeScript/Rust best-effort rules, non-function-symbol short-circuit, the
deleted-source-file fallback path in `_source_lines`, and the private
lexical helpers (`_header_colon_index`, `_next_statement_loop`,
`_operand_names`, `_bracket_identifiers`, `_container_kinds`) that the
end-to-end `perf_rules` tests in `tests/test_perf.py` cannot reach through
realistic Python source alone (malformed/synthetic token shapes, and a
source file that vanishes between parse and rule evaluation).
"""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.lang import parse_file
from frob.perf._rules import (
    _bracket_depths,
    _bracket_identifiers,
    _container_kinds,
    _header_colon_index,
    _method_call_in_loop,
    _next_statement_loop,
    _operand_names,
    _perf001_best_effort,
    _perf002_best_effort,
    _source_lines,
    perf_rules,
)


def _snapshot(root: Path):
    """Build a graph snapshot for `root`, matching `tests/test_perf.py`'s helper."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, matching `tests/test_perf.py`'s helper."""
    path = root / name
    path.write_text(src)
    return path


# frob:tests \
# tests/test_perf_rules_internals.py::test_method_call_in_loop_fires_at_depth_zero
def test_method_call_in_loop_fires_at_depth_zero():
    """`_method_call_in_loop` fires for `.<method>(` at a statement-level
    loop depth, and not for the same call outside any loop."""
    in_loop = ("for", "x", "in", "items", ":", "data", ".", "includes", "(", "x", ")")
    depths = _bracket_depths(in_loop)
    assert _method_call_in_loop(in_loop, depths, "includes") is True

    no_loop = ("data", ".", "includes", "(", "x", ")")
    depths2 = _bracket_depths(no_loop)
    assert _method_call_in_loop(no_loop, depths2, "includes") is False


# frob:tests \
# tests/test_perf_rules_internals.py::test_perf001_best_effort_dispatches_by_language
def test_perf001_best_effort_dispatches_by_language():
    """PERF001 best-effort: `.includes(` for typescript, `.contains(` for
    rust, and no rule at all for any other language string."""
    ts_tokens = ("for", "x", "in", "items", ":", "data", ".", "includes", "(", "x", ")")
    depths = _bracket_depths(ts_tokens)
    assert _perf001_best_effort(ts_tokens, depths, "typescript") is True

    rust_tokens = (
        "for",
        "x",
        "in",
        "items",
        ":",
        "data",
        ".",
        "contains",
        "(",
        "x",
        ")",
    )
    depths2 = _bracket_depths(rust_tokens)
    assert _perf001_best_effort(rust_tokens, depths2, "rust") is True

    assert _perf001_best_effort(ts_tokens, depths, "python") is False


# frob:tests \
# tests/test_perf_rules_internals.py::test_perf002_best_effort_typescript_only
def test_perf002_best_effort_typescript_only():
    """PERF002 best-effort only fires for TypeScript's `.indexOf(`; every
    other language (including Rust, which has no PERF002 rule at all)
    reports no hit."""
    ts_tokens = ("for", "x", "in", "items", ":", "data", ".", "indexOf", "(", "x", ")")
    depths = _bracket_depths(ts_tokens)
    assert _perf002_best_effort(ts_tokens, depths, "typescript") is True
    assert _perf002_best_effort(ts_tokens, depths, "rust") is False


# frob:tests \
# tests/test_perf_rules_internals.py::test_typescript_end_to_end_best_effort_via_perf_r\
# ules
def test_typescript_end_to_end_best_effort_via_perf_rules(tmp_path):
    """End-to-end sanity: a real TypeScript function's own enclosing braces
    push every statement-level loop to bracket depth 1, so the best-effort
    rules never fire through the real parse/token pipeline as it exists
    today -- documented here as a known gap alongside the direct
    `_method_call_in_loop`/`_perf00{1,2}_best_effort` unit tests above,
    which exercise the rule logic itself independent of that pipeline
    limitation."""
    src = (
        "function scan(items: number[], data: number[]): number {\n"
        "  let hits = 0;\n"
        "  for (const x of items) {\n"
        "    if (data.includes(x)) { hits++; }\n"
        "  }\n"
        "  return hits;\n"
        "}\n"
    )
    path = _write(tmp_path, "mod.ts", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF001" for v in violations)


# frob:tests tests/test_perf_rules_internals.py::test_typescript_no_hit_outside_loop
def test_typescript_no_hit_outside_loop(tmp_path):
    """The best-effort TypeScript rules do not fire without a loop gate."""
    src = "function has(data: number[], x: number): boolean {\n  return data.includes(x);\n}\n"
    path = _write(tmp_path, "mod.ts", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule in ("PERF001", "PERF002") for v in violations)


# frob:tests \
# tests/test_perf_rules_internals.py::test_non_function_symbol_yields_no_violations
def test_non_function_symbol_yields_no_violations(tmp_path):
    """A class symbol (not FUNCTION/METHOD) short-circuits with no findings --
    `_symbol_violations` only inspects function/method bodies."""
    src = "class Empty:\n    pass\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert violations == ()


# frob:tests \
# tests/test_perf_rules_internals.py::test_source_lines_missing_file_returns_empty
def test_source_lines_missing_file_returns_empty(tmp_path):
    """`_source_lines` returns `()` (not raise) when `path` cannot be
    opened -- the source moved/was deleted since parse."""
    missing = tmp_path / "gone.py"
    assert _source_lines(str(missing), (1, 3)) == ()


# frob:tests \
# tests/test_perf_rules_internals.py::test_perf_rules_falls_back_to_span_start_when_sou\
# rce_vanishes
def test_perf_rules_falls_back_to_span_start_when_source_vanishes(tmp_path):
    """When the source file is deleted between parse and rule evaluation,
    every line-anchoring helper falls back to the enclosing symbol's
    `span[0]` instead of raising."""
    src = (
        "def scan(items, haystack):\n"
        "    data = [1, 2, 3]\n"
        "    out = []\n"
        "    for x in items:\n"
        "        if x in data:\n"
        "            out.append(haystack.index(x))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    path.unlink()

    violations = perf_rules(snapshot, [parsed])

    assert violations, "expected PERF hits even with the source file gone"
    fn = next(s for s in parsed.symbols if s.qualname == "scan")
    for v in violations:
        assert v.line == fn.span[0]


# frob:tests \
# tests/test_perf_rules_internals.py::test_header_colon_index_returns_none_when_untermi\
# nated
def test_header_colon_index_returns_none_when_unterminated():
    """A malformed/truncated loop header with no closing `:` at depth 0
    reports `None` rather than raising or wrapping around."""
    tokens = ("for", "x", "in", "y")
    depths = (0, 0, 0, 0)
    assert _header_colon_index(tokens, depths, 0) is None


# frob:tests \
# tests/test_perf_rules_internals.py::test_next_statement_loop_returns_none_when_absent
def test_next_statement_loop_returns_none_when_absent():
    """No statement-level loop keyword after `start` reports `None`."""
    tokens = ("x", "=", "1")
    depths = (0, 0, 0)
    assert _next_statement_loop(tokens, depths, 0) is None


# frob:tests \
# tests/test_perf_rules_internals.py::test_operand_names_out_of_range_is_empty
def test_operand_names_out_of_range_is_empty():
    """An out-of-range `start` index (negative, or past the end) is treated
    as no operand rather than indexing an error."""
    tokens = ("x", "==", "y")
    assert _operand_names(tokens, -1, -1) == frozenset()
    assert _operand_names(tokens, 3, 1) == frozenset()


# frob:tests \
# tests/test_perf_rules_internals.py::test_operand_names_non_identifier_token_is_empty
def test_operand_names_non_identifier_token_is_empty():
    """A literal (non-identifier, non-bracket) operand token yields no names."""
    tokens = ("1", "==", "2")
    assert _operand_names(tokens, 0, -1) == frozenset()


# frob:tests \
# tests/test_perf_rules_internals.py::test_operand_names_call_and_subscript_unwind
def test_operand_names_call_and_subscript_unwind():
    """Call-paren and subscript-bracket operands unwind one level to their
    inner identifier (T-0246), symmetric in both directions."""
    call_tokens = ("f", "(", "x", ")", "==", "g", "(", "y", ")")
    assert _operand_names(call_tokens, 3, -1) == frozenset({"x"})
    assert _operand_names(call_tokens, 6, 1) == frozenset({"y"})

    subscript_tokens = ("a", "[", "i", "]", "==", "b", "[", "j", "]")
    assert _operand_names(subscript_tokens, 3, -1) == frozenset({"i"})
    assert _operand_names(subscript_tokens, 6, 1) == frozenset({"j"})


# frob:tests \
# tests/test_perf_rules_internals.py::test_bracket_identifiers_runs_off_the_end_without\
# _closing
def test_bracket_identifiers_runs_off_the_end_without_closing():
    """An unclosed bracket pair stops at the end of the token stream instead
    of indexing past it."""
    tokens = ("a", "[", "i")
    assert _bracket_identifiers(tokens, 2, 1) == frozenset({"i"})


# frob:tests \
# tests/test_perf_rules_internals.py::test_container_kinds_ignores_non_identifier_assig\
# nment_target
def test_container_kinds_ignores_non_identifier_assignment_target():
    """A non-identifier "name" slot (can't happen from real source, but the
    scan is purely lexical) is skipped rather than recorded."""
    tokens = ("1", "=", "[", "2", "]")
    assert _container_kinds(tokens) == {}
