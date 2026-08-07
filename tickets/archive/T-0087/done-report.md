## Done report

Root cause: `_walk_python._visit` only recognized a module-level constant
when it was wrapped in an `expression_statement` node. The grammar this
repo actually uses at runtime (`tree_sitter_language_pack.get_parser`,
via `frob.lang.parse_file`) emits top-level `assignment` nodes as direct
children of `module` -- it does not wrap them in `expression_statement`
at all. So this was not narrowly "misses call-expression RHS" but "misses
every module-level constant assignment, literal or call, when parsed
through the real production path" -- `_walk_python` alone (fed a tree
from the bare `tree_sitter_python` package) looked correct in isolation,
which is presumably how this slipped through before.

Changed:
- src/frob/lang/_walk_python.py::_const_symbol -- now accepts `node`
  being the `assignment` itself, in addition to the previous
  `expression_statement`-wraps-`assignment` shape.
- src/frob/lang/_walk_python.py::_visit -- the module-level dispatch
  branch now matches `node.type in ("expression_statement", "assignment")`
  instead of only `"expression_statement"`.

Before: `parse_file` on a file with `MAX_RETRIES = 3` or
`TRUST = Lattice(...)` at module scope produced zero CONST symbols.
After: both literal and call-expression module-level SCREAMING_CASE
assignments are extracted as CONST symbols (verified directly against
src/frob/strata/_models.py's TRUST/LABELS in manual repro, and via the
two new regression tests below).

Evidence:
- tests/test_lang.py::TestParsePython::test_module_level_literal_const_extracted
- tests/test_lang.py::TestParsePython::test_module_level_call_expression_const_extracted
- tests/test_lang.py full file: `uv run pytest tests/test_lang.py -q` -- 23 passed
- lang+graph suites: `uv run pytest tests/ -q -k "lang or graph"` -- all passed
- full suite: `uv run pytest -q` -- all green except the pre-existing,
  unrelated `tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function`
  failure (confirmed present on a clean `git stash` of this diff too --
  tracked separately as T-0117) and the known `test_scaffold_dx` slow-mark
  warning (T-0089), neither touched here.
- `frob check --ticket T-0087 --only gates --json` diagnostic count is
  identical before/after this change (112 diagnostics, same codes/counts)
  -- the newly-extracted CONST symbols (including TRUST/LABELS in
  src/frob/strata/_models.py) did not introduce new COV001/TEST002/DRIFT002
  violations in this repo's own gate run, so no fallout to handle.
- `frob check` (unscoped, whole repo) exits 0 both before and after.

Filed: none -- no out-of-scope work discovered beyond what T-0117 and
T-0089 already track.

Gates: frob check --ticket T-0087 clean (SCOPE001 on tickets.md and the
PERF003 note in tests/test_lang.py are pre-existing baseline artifacts of
`frob ticket start`/`sweep` writing to tickets.md and of an existing
nested-loop pattern earlier in the file; diagnostic count is unchanged
before/after this fix).
