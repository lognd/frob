## Done report

T-4417's land had no phase timestamps, so T-4408's 50+ minute land
could not be attributed to any phase without external ps inspection.
Added `_LandPhaseElapsedFilter`, a single `logging.Filter` on
`_land_cmd.py`'s shared logger that decorates every "ticket land: ..."
record with a `[+<elapsed>s]` prefix, timed from the first such line
this process emits -- one centralized helper rather than per-call-site
arithmetic, covering every existing (and future) phase-transition log
line in the file uniformly.

Evidence: tests/unit/test_land_phase_elapsed_logging.py's 3 tests
(monotonic elapsed values across two phase lines, non-phase lines left
untouched, and the lazy-start helper) all pass; `frob test` selected
and passed all 4 touched python tests.

check-repro note: `frob ticket evidence --check-repro` reports
TEST_ABSENT_AT_PARENT against this worktree's history -- the repro
test and its fix were committed together (T-2025's documented
limitation: no ref contains the test without the fix already
applied). Verified manually instead: reverting the `_LandPhaseElapsedFilter`
class/`_land_phase_elapsed_seconds` helper while keeping the test file
makes all 3 new tests fail (AttributeError on the removed names),
confirming they exercise real behavior, not a tautology.

Gates: `frob check --ticket T-4417` across gates-fast/gates-native/
gates-security/lint/static shows 0 errors attributable to this diff
after fixing COV001 (frob:doc on the new class/method), COV002
(frob:ticket on the new test methods), FMT001 (directive line
wrapping via `frob format --directives`), SCOPE001 (scope --add for
the new test file and the doc anchor), and DRIFT002 (a mid-wrap typo
in the frob:tests symref, now fixed). Remaining findings (DOC011
T-4313, MILE001, TICK004/TICK006 rot warnings) are pre-existing
repo-wide, unrelated to this ticket's touched files.

Filed: none.

### Changed
```
 docs/modules/tickets-landing.md               | 20 +++++++
 src/frob/app/ticket_runner/_land_cmd.py       | 82 +++++++++++++++++++++++++++
 tests/unit/test_land_phase_elapsed_logging.py | 76 +++++++++++++++++++++++++
 tickets/T-4417/ticket.md                      | 17 ++++++
 4 files changed, 195 insertions(+)
```

### Evidence
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_non_phase_log_lines_are_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_helper_starts_at_zero_on_first_call` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 4855 warning(s), 959 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, MILE001@tickets.md, TICK004@tickets.md, TICK006@tickets.md
