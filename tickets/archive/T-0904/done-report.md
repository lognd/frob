## Done report

Follow-up to T-0893 (landed as 352d2ef4): locks the size-cap/timeout guard
against silent regression. T-0893's own tests
(tests/test_lang.py::TestSizeCapAndTimeout) prove the guard works
correctly on the happy/unhappy path, but every fixture in the wider
`frob.lang` test suite is small and fast enough that a future refactor
which accidentally drops the `_check_size_cap`/`_run_parse_with_timeout`
calls from `_parse`/`_parse_strata_file` would pass every existing
behavioral test without anyone noticing -- exactly the "silent regression"
class this ticket exists to prevent.

Added `tests/unit/test_lang_parse_guard.py` with two locks:

1. `TestParseGuardIsWired` (structural, `inspect.getsource`): asserts
   `_parse` and `_parse_strata_file`'s own source text still references
   `_read_source_under_cap`/`_run_parse_with_timeout` by name. This is the
   most refactor-proof check possible -- even a change that keeps the
   guard reachable via some other code path but drops the direct call
   from these two functions fails this test.
2. `TestParseGuardIsInvoked` (behavioral, monkeypatch call-tracking):
   wraps `_check_size_cap`/`_run_parse_with_timeout` to record they were
   actually reached while parsing a real `.py` file (always runs) and a
   real `.strata` file (skipped if the litmus fixture is missing from the
   checkout). This catches the case the structural test cannot: a call
   left in dead/unreachable code.

No static lint was added -- the ticket's "if practical" qualifier is not
met here: `frob.lang` has no AST-level obligation-DSL mechanism today for
"function X must call function Y" the way `frob:tests`/`frob:doc` cover
symbol-to-test/symbol-to-doc edges; building one would be a new gate
mechanism, well beyond this ticket's scope. The two-layer test above
(structural + behavioral) is the practical substitute.

Scope stayed within T-0904's declared globs
(`src/frob/lang/__init__.py`, `tests/unit`) -- no source changes were
needed, only the new test file under `tests/unit/`.

Verification run in this worktree (post-merge of T-0893's landed main):
- `uv run pytest tests/unit/test_lang_parse_guard.py -p no:cacheprovider
  -q` -- 4 passed.
- `uv run ruff check tests/unit/test_lang_parse_guard.py` -- clean.
- `uv run ty check tests/unit/test_lang_parse_guard.py` -- clean.
- `uv run frob check --ticket T-0904 --only coverage --only scope
  --only prework --only test --only lang_conformance
  --only lang_project_conformance --only fmt` -- all clean (no scope
  extension needed, unlike T-0893).
- `uv run frob check --ticket T-0904 --only gates-native` -- clean.

### Changed
```
 tests/unit/test_lang_parse_guard.py | 127 +++++++++++
 tickets.md                          | 411 +++++++++++++++++++++++++++++++++++-
 2 files changed, 531 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_strata_file_source_calls_the_guard_helpers` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked::test_python_file_invokes_size_cap_and_timeout` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked::test_strata_file_invokes_size_cap_and_timeout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
