## Done report

Changed:
- tests/unit/test_app_runners_json_guard_t2492.py -- added `# noqa: F811`
  on each of the six `_real_console_handlers` fixture-parameter usages.

Investigation (per the coordinator's specific ask -- were the six
"redefinitions" identical or different, i.e. could some tests have been
exercising the wrong fixture since T-2492 landed): they were NEVER six
definitions at all. There is exactly ONE definition
(tests/unit/test_app_runners_batch6.py:536) and ONE cross-module import
of it (line 28 of this file, already carrying `# noqa: F401` per
DUP001's own precedent -- reuse the fixture rather than duplicate its
body). The six flagged sites are the SAME imported name used as a
pytest fixture parameter in six different test methods -- exactly how
pytest resolves a fixture by name, and the only way to consume an
imported fixture at all. Ruff's F811 does not model pytest's name-based
fixture injection for a cross-module import reused as a parameter (it
only recognizes the same-file def-then-parameter-shadow shape, which is
why the ORIGINAL definition site in test_app_runners_batch6.py never
tripped it). Confirmed by inspection: all six parameter lines are
byte-for-byte identical (`_real_console_handlers,`), and the full file
runs 6/6 green both before and after this fix (nothing about test
BEHAVIOR changed, only the lint annotation).

Conclusion: this is a lint false positive, not a functional bug. No
test was running against a wrong fixture; all six always received the
correct, single, real fixture.

Filed:
- T-2531 (E501 x3 in scripts/fleet_status.py, src/frob/graph/summary.py,
  src/frob/testing/_collect_kotlin.py, plus F401 in
  tests/unit/test_ticket_runner_repro_merge_base.py) -- T-2526's other 4
  bundled findings, a different root cause (genuine long lines / unused
  import) from this ticket's lint false positive. All 4 confirmed live
  via a direct `ruff check` run before filing. T-2526's own scope was
  narrowed to just the F811 file so this ticket stays a clean single-
  cause fix.
- (T-2529, filed then immediately dropped as a duplicate of this
  already-existing ticket, found before starting real work.)

Evidence:
- tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard::test_daemon_disabled_log_does_not_reach_stdout
- Full file run: 6 collected, 0 failed (both fixed and pre-fix trees)

Gates: `ruff check --select F811 tests/unit/test_app_runners_json_guard_t2492.py`
clean (0 errors, was 6). Pre-existing I001 (import-sort) finding in the
same file is untouched by this diff -- confirmed present at the parent
commit via `git show HEAD:<file> | ruff check --select I001 -`, unrelated
to F811, out of this ticket's declared scope.

### Changed
```
 tests/unit/test_app_runners_json_guard_t2492.py | 12 ++++----
 tickets/T-2526/ticket.md                        | 38 +++++++++++++++++++++----
 2 files changed, 39 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard::test_planted_leak_does_not_reach_stdout` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard::test_daemon_disabled_log_does_not_reach_stdout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2526/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2526/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2526/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2526/tests/unit/test_ticket_runner_repro_merge_base.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2526, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
