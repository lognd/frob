"""Tests for frob.perf: PERF001..PERF004, artifact round-trip, heat join.

# frob:ticket T-0021
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.graph import build_graph
from frob.lang import parse_file
from frob.perf import (
    heat,
    load_artifact,
    perf_rules,
    profile_command,
    redundant_computation_violations,
)


def _snapshot(root: Path):
    # frob:ticket T-0021
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _write(root: Path, name: str, src: str) -> Path:
    # frob:ticket T-0021
    path = root / name
    path.write_text(src)
    return path


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf001_fires_on_list_membership_in_loop(tmp_path):
    """PERF001 fires: `x in data` inside a loop where `data` is a list."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def scan(items):\n"
        "    data = [1, 2, 3]\n"
        "    hits = 0\n"
        "    for x in items:\n"
        "        if x in data:\n"
        "            hits += 1\n"
        "    return hits\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF001" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf001_does_not_fire_on_set_membership_in_loop(tmp_path):
    """PERF001 does not fire when the container is already a set -- the
    false-positive guard docs/modules/perf.md and the ticket both name as
    priority #1."""
    # frob:ticket T-0021
    src = (
        "def scan(items):\n"
        "    data = {1, 2, 3}\n"
        "    hits = 0\n"
        "    for x in items:\n"
        "        if x in data:\n"
        "            hits += 1\n"
        "    return hits\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF001" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf001_does_not_fire_outside_a_loop(tmp_path):
    """PERF001 does not fire when the membership test is not inside a
    for/while body, even against a plain list."""
    # frob:ticket T-0021
    src = "def check_one(data, x):\n    data = [1, 2, 3]\n    return x in data\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF001" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf002_fires_on_index_call_in_loop(tmp_path):
    """PERF002 fires: `.index()` call inside a loop."""
    # frob:ticket T-0021
    src = (
        "def find_all(items, haystack):\n"
        "    out = []\n"
        "    for x in items:\n"
        "        out.append(haystack.index(x))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF002" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf002_does_not_fire_outside_a_loop(tmp_path):
    """PERF002 does not fire on a single `.index()` call with no loop."""
    # frob:ticket T-0021
    src = "def find_one(haystack, needle):\n    return haystack.index(needle)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF002" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_fires_on_nested_loop_equality_join(tmp_path):
    """PERF003 fires: nested loops comparing items with `==`."""
    # frob:ticket T-0021
    src = (
        "def join(a, b):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            if x == y:\n"
        "                out.append(x)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_does_not_fire_on_single_loop(tmp_path):
    """PERF003 does not fire when there is only one loop."""
    # frob:ticket T-0021
    src = "def total(a):\n    out = 0\n    for x in a:\n        out += x\n    return out\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_fires_on_sort_in_loop(tmp_path):
    """PERF004 fires: `sorted()` call inside a loop over unchanged data."""
    # frob:ticket T-0021
    src = (
        "def rank(rounds, data):\n"
        "    out = []\n"
        "    for r in rounds:\n"
        "        out.append(sorted(data))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_does_not_fire_on_sort_outside_a_loop(tmp_path):
    """PERF004 does not fire on a single top-level `sorted()` call."""
    # frob:ticket T-0021
    src = "def rank_once(data):\n    return sorted(data)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_does_not_fire_on_sibling_comprehensions(tmp_path):
    """PERF003 does not fire on two sibling comprehensions/generator
    expressions plus an unrelated `==` -- T-0161's headline false-positive
    class (comprehension `for` is not a loop statement)."""
    # frob:ticket T-0161
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def check(records, expected):\n"
        "    names = {r.name for r in records}\n"
        "    valid = any(r.ok for r in records)\n"
        "    assert len(names) == expected\n"
        "    return valid\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_does_not_fire_on_sibling_statement_loops(tmp_path):
    """PERF003 does not fire on two sibling (not nested) statement-level
    `for` loops, even with an unrelated `==` elsewhere in the function."""
    # frob:ticket T-0161
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def summarize(a, b, total):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        out.append(x)\n"
        "    for y in b:\n"
        "        out.append(y)\n"
        "    assert len(out) == total\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_fires_on_nested_join_with_intervening_statement(tmp_path):
    """PERF003 fires on a real nested equality join even when a setup
    statement (an accumulator init, a guard, ...) sits between the outer
    loop's header and the inner loop -- reviewer-caught round-2 regression
    (T-0161): round 1's "inner loop must be the literal next token after
    the outer colon" adjacency check silently missed this common shape."""
    # frob:ticket T-0161
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def join(a, b):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        y0 = 0\n"
        "        for y in b:\n"
        "            if x == y:\n"
        "                out.append(x)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_does_not_fire_when_sorted_is_the_loop_iterable(tmp_path):
    """PERF004 does not fire on `for x in sorted(data):` -- `sorted()` there
    is the loop's own iterable, evaluated once, not resorted per
    iteration."""
    # frob:ticket T-0161
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def visit(paths):\n"
        "    out = []\n"
        "    for path in sorted(paths):\n"
        "        out.append(path)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_does_not_fire_on_sort_after_loop_same_indent(tmp_path):
    """T-0367: PERF004 does not fire on a `sorted()`/`.sort()` call that
    occurs textually AFTER a `for` loop at the same (or an outer) indent --
    it runs once per function call, not once per iteration. The old
    token/bracket-depth heuristic (`_loop_gate`) is indentation-blind and
    cannot see that this sort is a SIBLING statement, not a descendant of
    the loop body; the fix is AST body-field containment
    (`_enclosing_loop_body_hit`)."""
    # frob:ticket T-0367
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def process(items):\n"
        "    out = []\n"
        "    for x in items:\n"
        "        out.append(x)\n"
        "    out.sort()\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_does_not_fire_on_sorted_call_after_loop_same_indent(tmp_path):
    """T-0367: same false-positive shape as the `.sort()` sibling above, but
    for the `sorted()` free-function call form -- both call shapes
    (`_is_sort_call`) must be indentation/AST-aware, not just one."""
    # frob:ticket T-0367
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def process(items):\n"
        "    out = []\n"
        "    for x in items:\n"
        "        out.append(x)\n"
        "    return sorted(out)\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_still_fires_on_sort_nested_deeper_inside_loop_body(tmp_path):
    """T-0367: a genuine in-loop sort still fires even when nested a further
    level deep inside the loop body (an `if` inside the `for`) -- the
    AST-aware fix must not lose true positives that are merely more
    indented than the simple case."""
    # frob:ticket T-0367
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def rank(rounds, data):\n"
        "    out = []\n"
        "    for r in rounds:\n"
        "        if r:\n"
        "            out.append(sorted(data))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_does_not_fire_on_sorted_generator_no_preceding_loop(tmp_path):
    """PERF004 does not fire on `sorted(x for x in y)` with no preceding
    statement-level loop -- the generator's own `for` is bracket-depth
    >= 1, not a loop statement, so it must not itself satisfy the loop
    gate for its enclosing `sorted()` call."""
    # frob:ticket T-0161
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = "def report(matched):\n    return sorted(m.id for m in matched)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf002_anchors_to_index_call_line_not_def_line(tmp_path):
    """T-0230: a PERF002 finding anchors to the actual `.index()` call
    site's line, not the enclosing `def` line -- the sibling-repo pilot
    gap (lithos audit.py:450 PERF002 while the `.index()` calls sit at
    465-466)."""
    # frob:ticket T-0230
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def find_all(items, haystack):\n"
        "    out = []\n"
        "    for x in items:\n"
        "        out.append(haystack.index(x))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    hit = next(v for v in violations if v.rule == "PERF002")
    assert hit.line == 4


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf004_anchors_to_sort_call_line_not_def_line(tmp_path):
    """T-0230: a PERF004 sorted-in-loop finding anchors to the `sorted()`
    call line, not the enclosing `def` line."""
    # frob:ticket T-0230
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def rank(rounds, data):\n"
        "    out = []\n"
        "    for r in rounds:\n"
        "        out.append(sorted(data))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    hit = next(v for v in violations if v.rule == "PERF004")
    assert hit.line == 4


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_anchors_to_equality_line_not_def_line(tmp_path):
    """T-0230: a PERF003 finding anchors to the `==` comparison's line, not
    the enclosing `def` line (the rust conformance.rs:31-pointing-at-the-
    fn-signature gap from the same pilot report)."""
    # frob:ticket T-0230
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def join(a, b):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            if x == y:\n"
        "                out.append(x)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    hit = next(v for v in violations if v.rule == "PERF003")
    assert hit.line == 5


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_fires_on_call_operand_join(tmp_path):
    """T-0246: a real nested join comparing DERIVED values -- `f(x) ==
    g(y)` with `x`/`y` the loop variables inside call parens -- is now
    correlated and fires, extending `_operand_names`'s one-level unwind
    from subscripts to call parens."""
    # frob:ticket T-0246
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def join(a, b):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            if f(x) == g(y):\n"
        "                out.append(x)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF003" for v in violations)


# frob:waive DUP001 reason="parallel perf-rule case table: independent PERF-rule \
# fire/no-fire cases sharing an arrange-act scaffold by design (one src snippet + one \
# assertion per case); extracting would obscure per-case intent"
def test_perf003_call_operand_join_stays_narrow_no_recursive_unwind(tmp_path):
    """T-0246: the call-paren unwind stops at one level -- an unrelated
    trailing `==` after two sibling (non-nested) loops, where the outer
    loop's own bound variable is buried two calls deep on the far side,
    must not spuriously correlate (the same false-positive discipline the
    subscript unwind already keeps, applied to the new call-paren path)."""
    # frob:ticket T-0246
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def summarize(a, b, total):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        out.append(x)\n"
        "    for y in b:\n"
        "        out.append(y)\n"
        "    assert len(out) == f(g(total))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF003" for v in violations)


def test_perf005_fires_on_unproven_self_recursion(tmp_path):
    """PERF005: a self-recursive function with no descent/guard shape and
    no `frob:invariant terminates` directive is unproven -- ERROR."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = "def loop_forever(x):\n    return loop_forever(x)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    hit = next(v for v in violations if v.rule == "PERF005")
    # T-0290 lands at WARN until the ~45 pre-existing sites are swept
    # (then promoted to ERROR); see _recursion.py severity note.
    assert hit.severity.value == "warn"


def test_perf005_does_not_fire_on_structural_descent_with_guard(tmp_path):
    """PERF005 is silent when the recursive call narrows on a decreasing
    integer measure AND the function has a base-case guard -- the proven,
    decidable fragment."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = (
        "def countdown(n):\n"
        "    if n <= 0:\n"
        "        return 0\n"
        "    return countdown(n - 1)\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF005" for v in violations)


def test_perf005_silenced_by_reasoned_termination_directive(tmp_path, monkeypatch):
    """The `frob:invariant terminates reason="..." measure="..."` escape
    hatch (T-0290) suppresses PERF005 even with no provable descent shape."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    # `_display_path` relativizes to cwd; chdir so the directly-parsed
    # ParsedFile's path matches the root-relative symref build_graph binds
    # the frob:invariant edge to.
    monkeypatch.chdir(tmp_path)
    src = (
        '# frob:invariant terminates reason="ackermann on bounded fuel arg"'
        ' measure="fuel"\n'
        "def weird(fuel, x):\n"
        "    return weird(fuel, x)\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF005" for v in violations)


def test_perf006_fires_on_unbounded_tail_recursion(tmp_path):
    """PERF006: tail recursion (`return f(...)` as the whole return) with
    no proven depth bound -- Python has no TCO, so this is a stack-overflow
    hazard, not just an unproven-termination finding."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = "def tail(x):\n    return tail(x)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF006" for v in violations)


def test_perf006_silenced_by_reasoned_termination_directive(tmp_path, monkeypatch):
    """The same reasoned directive that proves PERF005 also silences
    PERF006 -- a proven depth bound is also a proven termination measure."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    monkeypatch.chdir(tmp_path)
    src = (
        '# frob:invariant terminates reason="bounded by fuel param"'
        ' measure="fuel"\n'
        "def tail(fuel):\n    return tail(fuel)\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF006" for v in violations)


def test_perf005_fires_on_mutual_recursion(tmp_path):
    """PERF005 detects same-file mutual recursion (A calls B, B calls A),
    not just direct self-recursion."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = (
        "def is_even(n):\n"
        "    return is_odd(n)\n\n"
        "def is_odd(n):\n"
        "    return is_even(n)\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    refs = {
        (v.symref or "").rsplit("::", 1)[-1] for v in violations if v.rule == "PERF005"
    }
    assert "is_even" in refs
    assert "is_odd" in refs


def test_perf005_does_not_fire_on_non_recursive_function(tmp_path):
    """A plain, non-recursive function never trips PERF005/PERF006."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = "def add(a, b):\n    return a + b\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule in ("PERF005", "PERF006") for v in violations)


def test_perf005_fires_when_descent_is_outside_the_call_args(tmp_path):
    """Reviewer-caught bug (T-0290 round 2): `loop_forever(n) - 1 if n > 0
    else 0` puts the `- 1` OUTSIDE the recursive call's own argument list --
    `n` itself is never narrowed inside the call -- so this is genuine
    infinite recursion and PERF005 MUST still fire. The prior fixed
    `tokens[i+2:i+12]` lookahead window scanned past the call's own parens
    into the surrounding expression and misread the outer `- 1` as descent,
    silently missing this case."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = "def loop_forever(n):\n    return loop_forever(n) - 1 if n > 0 else 0\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF005" for v in violations)


def test_perf005_does_not_fire_on_super_init_call(tmp_path):
    """Reviewer-caught bug (T-0290 round 2): `super().__init__()` inside
    `__init__` is NOT self-recursion -- the bare `identifier(` scan with no
    receiver awareness misread it as a recursive call to `__init__` and
    produced ~50 false-positive findings across frob's own constructors.
    Call detection must be receiver-aware: an unqualified call, or a call
    qualified by `self`, counts; `super().foo()` never does."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = (
        "class Filter:\n"
        "    def __init__(self, name):\n"
        "        super().__init__()\n"
        "        self.name = name\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule in ("PERF005", "PERF006") for v in violations)


def test_perf005_does_not_pair_same_named_methods_across_classes(tmp_path):
    """Reviewer-caught bug (T-0290 round 2): mutual-recursion pairing must
    require the same enclosing scope (class), not just a matching short
    name anywhere in the file. `Alpha.foo`/`Alpha.bar` are a real,
    intra-class mutual-recursion pair (`foo` calls `self.bar()`, `bar`
    calls `self.foo()`). `Beta.bar` is UNRELATED -- it calls `self.foo()`,
    but `Beta` has no `foo` of its own, so this can never actually be
    recursion at runtime. The pre-fix, scope-blind algorithm paired
    `Beta.bar` with `Alpha.foo` anyway (both share the file, and their
    short names cross-reference) -- a spurious cross-class finding this
    test pins closed."""
    # frob:ticket T-0290
    # frob:tests src/frob/perf/_recursion.py::recursion_rules
    src = (
        "class Alpha:\n"
        "    def foo(self):\n"
        "        return self.bar()\n"
        "    def bar(self):\n"
        "        return self.foo()\n\n"
        "class Beta:\n"
        "    def bar(self):\n"
        "        return self.foo()\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    beta_refs = [
        v
        for v in violations
        if v.rule in ("PERF005", "PERF006")
        and v.symref
        and v.symref.endswith("::Beta.bar")
    ]
    assert beta_refs == []


def test_profile_command_and_load_artifact_round_trip(tmp_path):
    """`profile_command` writes an artifact `load_artifact` can read back."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_profile.py::profile_command
    # frob:tests src/frob/perf/_profile.py::load_artifact
    (tmp_path / "workload.py").write_text(
        "total = 0\nfor i in range(1000):\n    total += i\n"
    )
    result = profile_command(["workload.py"], tmp_path)
    assert result.is_ok, result.err
    artifact = result.danger_ok

    loaded = load_artifact(tmp_path)
    assert loaded.is_ok, loaded.err
    assert loaded.danger_ok.sha == artifact.sha

    by_ref = load_artifact(tmp_path, ref=artifact.sha)
    assert by_ref.is_ok
    assert by_ref.danger_ok.sha == artifact.sha


def test_load_artifact_no_artifact_is_err(tmp_path):
    """`load_artifact` returns `Err(NoArtifact)` when nothing was profiled."""
    # frob:ticket T-0021
    result = load_artifact(tmp_path)
    assert result.is_err
    assert result.danger_err.name == "NoArtifact"


def _init_hot_cold_workload(tmp_path: Path) -> None:
    """Git-init `tmp_path` and drop a `workload.py` with a hot/cold function
    pair -- the fixture shared by the heat-join test below."""
    # frob:ticket T-0021
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _write(
        tmp_path,
        "workload.py",
        "def hot():\n"
        "    total = 0\n"
        "    for i in range(200000):\n"
        "        total += i\n"
        "    return total\n"
        "\n"
        "def cold():\n"
        "    return 1\n"
        "\n"
        "hot()\n"
        "cold()\n",
    )


def test_heat_joins_pstats_rows_onto_symbol_spans(tmp_path):
    """`heat` attributes profiled time to the enclosing symbol and ranks by
    cum_s desc."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_heat.py::heat
    _init_hot_cold_workload(tmp_path)
    result = profile_command(["workload.py"], tmp_path)
    assert result.is_ok, result.err
    artifact = result.danger_ok

    snapshot = _snapshot(tmp_path)
    report = heat(artifact, snapshot)

    entries_by_ref = {entry.ref: entry for entry in report.entries}
    assert "workload.py::hot" in entries_by_ref
    hot_entry = entries_by_ref["workload.py::hot"]
    assert hot_entry.cum_s >= 0.0
    if len(report.entries) > 1:
        assert report.entries[0].cum_s >= report.entries[-1].cum_s


def test_join_smells_attaches_rule_ids_by_ref():
    """`join_smells` attaches PERF rule ids onto matching entries only."""
    # frob:tests src/frob/perf/_heat.py::join_smells kind="unit"
    from frob.perf._heat import join_smells
    from frob.perf._models import HeatEntry, HeatReport

    report = HeatReport(
        entries=(
            HeatEntry(ref="a.py::f", cum_s=1.0, self_s=1.0, ncalls=1),
            HeatEntry(ref="a.py::g", cum_s=2.0, self_s=2.0, ncalls=1),
        ),
        unattributed_s=0.0,
    )
    updated = join_smells(report, {"a.py::f": ("PERF001",)})
    smells_by_ref = {e.ref: e.smells for e in updated.entries}
    assert smells_by_ref["a.py::f"] == ("PERF001",)
    assert smells_by_ref["a.py::g"] == ()


def test_render_bar_scales_fill_to_ratio():
    """`render_bar` fills proportionally to cum_s/max_s, uncolored when
    color=False."""
    # frob:tests src/frob/perf/_heat.py::render_bar kind="unit"
    from frob.perf._heat import render_bar

    empty = render_bar(0.0, 10.0, color=False)
    full = render_bar(10.0, 10.0, color=False)
    half = render_bar(5.0, 10.0, color=False)
    assert empty == "-" * 30
    assert full == "#" * 30
    assert half.count("#") == 15


def test_profile_artifact_names_are_sha_derived():
    """`pstats_name`/`meta_name` derive their basenames from the artifact sha."""
    # frob:tests src/frob/perf/_models.py::ProfileArtifact.pstats_name kind="unit"
    # frob:tests src/frob/perf/_models.py::ProfileArtifact.meta_name kind="unit"
    from datetime import datetime

    from frob.perf._models import ProfileArtifact

    artifact = ProfileArtifact(
        sha="deadbeef", argv=("workload.py",), created=datetime.now(), total_s=0.1
    )
    assert artifact.pstats_name == "deadbeef.pstats"
    assert artifact.meta_name == "deadbeef.json"


def test_profile_records_workload_exit_code(tmp_path):
    """T-0027: a failing workload is profiled anyway and its exit code is
    recorded on the artifact, not masked as a spawn failure."""
    (tmp_path / "fail.py").write_text("import sys\nsum(range(100))\nsys.exit(3)\n")
    result = profile_command(["fail.py"], tmp_path)
    assert result.is_ok, result.err
    assert result.danger_ok.exit_code == 3


def test_profile_clean_workload_exit_zero(tmp_path):
    (tmp_path / "ok.py").write_text("sum(range(1000))\n")
    result = profile_command(["ok.py"], tmp_path)
    assert result.is_ok, result.err
    assert result.danger_ok.exit_code == 0


def test_profile_command_strips_leading_python_interpreter(tmp_path):
    """T-0027/T-0021: a caller-supplied leading `python`/`python3` argv
    entry is stripped before spawning the harness (the harness itself
    supplies the interpreter) -- proves `_harness_argv`'s strip branch."""
    # frob:ticket T-0021
    (tmp_path / "ok.py").write_text("sum(range(10))\n")
    result = profile_command(["python", "ok.py"], tmp_path)
    assert result.is_ok, result.err
    assert result.danger_ok.exit_code == 0


def test_load_artifact_missing_ref_is_err(tmp_path):
    """`load_artifact(ref=...)` for a sha with no matching sidecar is
    `Err(NoArtifact)`, not a crash -- proves `_choose_meta_path`'s
    ref-not-found branch."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_profile.py::load_artifact
    (tmp_path / "ok.py").write_text("sum(range(10))\n")
    profiled = profile_command(["ok.py"], tmp_path)
    assert profiled.is_ok, profiled.err

    result = load_artifact(tmp_path, ref="deadbeefdeadbeef")
    assert result.is_err
    assert result.danger_err.name == "NoArtifact"


def test_load_artifact_bad_json_sidecar_is_bad_artifact(tmp_path):
    """A meta sidecar that fails to parse as `ProfileArtifact` JSON is
    `Err(BadArtifact)` -- proves `load_artifact`'s parse-failure branch."""
    # frob:ticket T-0021
    perf_dir = tmp_path / ".frob" / "perf"
    perf_dir.mkdir(parents=True)
    (perf_dir / "bogus.json").write_text("not json at all")

    result = load_artifact(tmp_path)
    assert result.is_err
    assert result.danger_err.name == "BadArtifact"


def test_load_artifact_missing_pstats_is_bad_artifact(tmp_path):
    """A valid meta sidecar whose `.pstats` file was deleted out from under
    it is `Err(BadArtifact)` -- proves `load_artifact`'s missing-pstats
    branch."""
    # frob:ticket T-0021
    (tmp_path / "ok.py").write_text("sum(range(10))\n")
    profiled = profile_command(["ok.py"], tmp_path)
    assert profiled.is_ok, profiled.err
    sha = profiled.danger_ok.sha

    perf_dir = tmp_path / ".frob" / "perf"
    (perf_dir / f"{sha}.pstats").unlink()

    result = load_artifact(tmp_path, ref=sha)
    assert result.is_err
    assert result.danger_err.name == "BadArtifact"


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


def _git_add(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


class TestPerf007RedundantComputation:
    """T-0413 (the PERF META-GAP): the same `frob.toml`-configured expensive
    call invoked from 2+ distinct top-level symbols with no shared cache is
    PERF007; a single call site, or a cached definition, is not."""

    def test_two_stages_calling_the_same_uncached_parse_is_flagged(
        self, tmp_path: Path
    ) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "frob.toml",
            '[[perf.heavy]]\nname = "heavy_parse"\n',
        )
        src = (
            "def heavy_parse(path):\n"
            "    return open(path).read()\n\n\n"
            "def stage_a(path):\n"
            "    return heavy_parse(path)\n\n\n"
            "def stage_b(path):\n"
            "    return heavy_parse(path)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        _git_add(tmp_path)
        parsed = parse_file(path).danger_ok
        snapshot = _snapshot(tmp_path)

        violations = redundant_computation_violations(tmp_path, [parsed])
        assert any(v.rule == "PERF007" for v in violations)
        # And wired all the way through perf_rules, per T-0413's plan.
        assert any(v.rule == "PERF007" for v in perf_rules(snapshot, [parsed]))

    def test_single_shared_call_site_is_not_flagged(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "frob.toml",
            '[[perf.heavy]]\nname = "heavy_parse"\n',
        )
        src = (
            "def heavy_parse(path):\n"
            "    return open(path).read()\n\n\n"
            "def stage_a(path):\n"
            "    return heavy_parse(path)\n\n\n"
            "def stage_b(path, cached_text):\n"
            "    return cached_text\n"
        )
        path = _write(tmp_path, "mod.py", src)
        _git_add(tmp_path)
        parsed = parse_file(path).danger_ok

        violations = redundant_computation_violations(tmp_path, [parsed])
        assert not any(v.rule == "PERF007" for v in violations)

    def test_cached_definition_suppresses_the_warning(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "frob.toml",
            '[[perf.heavy]]\nname = "heavy_parse"\n',
        )
        src = (
            "@memoize_per_run\n"
            "def heavy_parse(path):\n"
            "    return open(path).read()\n\n\n"
            "def stage_a(path):\n"
            "    return heavy_parse(path)\n\n\n"
            "def stage_b(path):\n"
            "    return heavy_parse(path)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        _git_add(tmp_path)
        parsed = parse_file(path).danger_ok

        violations = redundant_computation_violations(tmp_path, [parsed])
        assert not any(v.rule == "PERF007" for v in violations)

    def test_no_config_means_no_perf007_checking(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        src = (
            "def heavy_parse(path):\n"
            "    return open(path).read()\n\n\n"
            "def stage_a(path):\n"
            "    return heavy_parse(path)\n\n\n"
            "def stage_b(path):\n"
            "    return heavy_parse(path)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        _git_add(tmp_path)
        parsed = parse_file(path).danger_ok

        violations = redundant_computation_violations(tmp_path, [parsed])
        assert violations == ()


def test_perf_end_to_end_profile_load_and_heat(tmp_path):
    # frob:tests src/frob/perf kind="integration"
    # Drive the whole perf boundary: profile a real workload to a stored
    # artifact, reload it by sha, and join its pstats rows onto the graph.
    # frob:ticket T-0021
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "work.py").write_text(
        "def busy():\n    return sum(range(50000))\n\n\nbusy()\n",
        encoding="utf-8",
    )
    profiled = profile_command(["src/work.py"], tmp_path)
    assert profiled.is_ok, profiled.err

    reloaded = load_artifact(tmp_path, profiled.danger_ok.sha)
    assert reloaded.is_ok, reloaded.err

    snapshot = _snapshot(tmp_path)
    report = heat(reloaded.danger_ok, snapshot)
    assert report.unattributed_s >= 0.0
