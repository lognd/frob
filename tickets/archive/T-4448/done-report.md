## Done report

T-1934's finished-signal detector missed a real unlanded worktree in production (t-4442/t-4446); added an independent, broader ticket-touched/ahead-of-main gate that cannot share that failure mode, with real-repo repro tests proving both the pre-fix miss and the post-fix keep. Remaining frob check findings (DRIFT001 on src/frob/doctor.py, REF002 on docs/design/macos-portability.md) are pre-existing baseline drift on unrelated files never touched by this diff, confirmed via git diff main..HEAD -- out of this ticket's scope.

### Changed
```
 src/frob/tickets/_worktree_sweep.py            | 161 ++++++++++++++++++++++++-
 tests/unit/rapid_sweep_suite/test_worktrees.py | 137 +++++++++++++++++++++
 tickets/T-4448/ticket.md                       |   4 +
 3 files changed, 297 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_one_commit_ahead_is_kept` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_zero_ahead_ticket_done_is_removed` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_ahead_survives_even_with_done_report` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4828 warning(s), 967 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
