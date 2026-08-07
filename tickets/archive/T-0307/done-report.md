## Done report

Counter located: `_test001_002_one` and `_test003_check_package` in
`src/frob/gates/__init__.py` both used `len(valid)` -- the count of
*edges* returned by `_valid_edges` -- as the collected-case count.
`_valid_edges` only answers "does this directive have any execution
evidence at all" (one bool per edge, via `_node_id_collected`'s exact-or-
`[prefix]` match), so a `frob:tests` directive bound to a
`@pytest.mark.parametrize`'d test always contributed exactly 1 case no
matter how many `[case-id]` variants pytest actually collected --
TEST001 saw the edge and passed, but TEST002/TEST003's `min_*_cases`
minimum was checked against 1, not N.

Fix: added `_case_count(valid_edges, tests) -> int`
(`src/frob/gates/__init__.py`, near `_inferred_unit_cases`) that, for
each already-validated edge, counts every matching collected node id --
the exact `path::func` id if present, plus each `path::func[case-id]`
parametrize expansion, each as its own case -- falling back to 1 for an
edge with no execution-based match at all (the ts/c/cpp structural
fallback branch of `_valid_edges`, which has no pytest/cargo evidence to
expand). `_test001_002_one` and `_test003_check_package` now call
`_case_count(valid, tests)` instead of `len(valid)`. `_node_id_collected`
and `_valid_edges` themselves are unchanged (TEST001's edge-exists check
is correct as-is); `_inferred_unit_cases` (convention-matched tests, no
explicit edge) already counted each collected node id individually, so
it needed no change. Rust `cargo test --list` ids carry no `[param]`
suffix (proptest! macro expansion is a distinct problem, tracked
separately as T-0318), so this pass is python-parametrize-focused per
the ticket's priority; the `[...]`-suffix stripping is otherwise
language-agnostic and will also correctly count any future collector
that does emit bracketed variant ids.

Litmus proving the fix: `tests/test_gates.py::TestTestGate::test_test002_parametrized_test_counts_each_case`
-- a `frob:tests` directive bound to a 3-case
`@pytest.mark.parametrize`'d `test_helper`, `TestPolicy(min_unit_cases=3)`,
3 collected node ids `test_helper[1]`/`[2]`/`[3]`; asserts neither
TEST001 nor TEST002 fires (pre-fix this failed: `effective=1 < 3` fired
TEST002). Also added `tests/test_gates.py::TestTestGate::test_case_count_direct`,
direct unit coverage of `_case_count` proving 3 collected node ids ->
count 3, and a validated edge with zero execution-based matches ->
count 1 (native-fallback parity preserved).

Changed:
- src/frob/gates/__init__.py::_case_count (new)
- src/frob/gates/__init__.py::_test001_002_one
- src/frob/gates/__init__.py::_test003_check_package

Evidence:
- tests/test_gates.py::TestTestGate::test_test002_parametrized_test_counts_each_case
- tests/test_gates.py::TestTestGate::test_case_count_direct
- tests/test_gates.py::TestTestGate (all 22 cases green: `uv run pytest tests/test_gates.py -k TestTestGate -q`)
- tests/test_gates.py, tests/unit/test_check.py, tests/unit/deploy, tests/test_testing.py all green:
  `uv run pytest tests/test_gates.py tests/unit/test_check.py tests/unit/deploy tests/test_testing.py -q`
- `uv run ruff check` / `uv run ruff format --check` / `uv run ty check` all clean on touched files
- `make coverage` clean; `uv run frob check` -> gates: 0 errors, 0 warnings, 204 waived (pre-existing waivers, no new violations)
- `git diff main --diff-filter=D --stat` empty (deletion-filter clean)

Filed: none (rust proptest!-block multi-case counting for TEST003 was
already filed separately as T-0318 before this ticket started; no new
out-of-scope work discovered)

Gates: `frob check` clean, 0 errors/0 warnings within scoped files; no
new waivers added.
