## Done report

Relocated `frob ticket doable`'s per-invocation diagnostic wall (over-broad
scope nudges) into `frob check`'s `tickets` stage as two new gate rules:
TICK009 (scope-breadth nudge, wraps the existing T-0453
`large_glob_warnings` verbatim) and TICK010 (stale cross-worktree lease
report, a direct read-only scan of `.git/frob-leases/*.json` against each
lease's recorded worktree path). `frob ticket doable` now prints a single
summary count line (`_render_scope_breadth_summary`) instead of one
`WARNING:` line per nudge per invocation -- observed collapsing 65
repeated warning lines down to one. TICK010 must run before any call that
touches `frob.tickets.read_all_leases` (TICK007, via `doable`), since that
call opportunistically unlinks a lease the moment it confirms the
worktree is gone; `tickets_gate` computes TICK010 first for exactly this
reason.

### Changed
```
 docs/modules/gates.md                              |  53 +++++++++
 docs/modules/tickets.md                            |  16 ++-
 src/frob/app/ticket_runner.py                      |  40 +++++--
 src/frob/gates/__init__.py                         | 131 +++++++++++++++++++-
 tests/test_gates_tick009_tick010.py                | 132 +++++++++++++++++++++
 .../unit/test_app_runners_t0714_doable_summary.py  |  65 ++++++++++
 tickets.md                                         |  51 +++++++-
 7 files changed, 469 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_precisely_scoped_ticket_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_terminal_state_ticket_excluded` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_worktree_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_five_stale_leases_each_reported_exactly_once` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_no_leases_directory_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_no_nudges_prints_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 12 error(s), 3517 warning(s), 358 waived
- error-findings: COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@src/frob/app/ticket_runner.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_gates_tick009_tick010.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
