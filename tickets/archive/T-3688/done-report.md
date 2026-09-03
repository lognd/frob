## Done report

Changed:
- tests/unit/test_conftest_midrun_watchdog.py (ruff-format only)
- tests/test_lang.py::TestBash.test_parse_bash_produces_a_tree (removed
  stale frob:tests directive; added frob:ticket T-3688 edges)
- tickets/T-3604/ticket.md (evidence rebind: stale
  test_step_has_continue_on_error -> test_step_has_no_continue_on_error)
- tickets/T-3053/ticket.md (unblocked stale T-3088 edge; priority
  critical -> high)

Evidence: tests/test_lang.py::TestBash::test_walks_top_level_function
(covers the _walk_bash reachability this ticket's directive cleanup
touches); ruff-format and gate:COV/gate:TICK measured directly via
scoped frob check.

Filed: none

Gates: frob check --ticket T-3688 clean on gate:SCOPE, gate:PRE (after
re-sweep), gate:COV, gate:TICK. gate:DEPR/gate:PERF/gate:WAIVE remain
FAIL but are pre-existing repo-wide findings outside this ticket's scope
(PERF errors are both in src/frob/refactor/**, off-limits to this series
per fleet discipline).

### Changed
```
 tests/test_lang.py                          |  7 ++++++-
 tests/unit/test_conftest_midrun_watchdog.py | 12 +++++++-----
 tickets/T-3053/ticket.md                    | 16 +++++++++++++---
 tickets/T-3604/ticket.md                    |  9 ++++++++-
 tickets/T-3688/ticket.md                    | 10 ++++++++++
 5 files changed, 44 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestBash::test_walks_top_level_function` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 4265 warning(s), 909 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, DEPR006@frob-deprecated-baseline.lock.json, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, WAIVE011@frob-ratchet.lock.json
