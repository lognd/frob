## Done report

T-1523: this is a targeted slice of the ticket's own "Option A" design
sketch (checkpoint the killable post-commit window, T-1495 point 4), NOT
the full Option A "every intermediate state durable" scope or Option B's
separate `--verify-only` CLI verb -- the ticket body itself says either
option needs its own design doc; this closes the specific, highest-risk
piece: `_post_land_unscoped_error_sweep` (the only post-commit step that
can still mutate/revert `root`, per T-1514's own docstring, which already
narrowed the pre-commit half of this same gap).

New T-1523 marker (`.frob/land-verify-pending/<ticket_id>.json`,
`src/frob/tickets/_land.py`: `_write_post_land_verify_marker`/
`_clear_post_land_verify_marker`/`_stale_post_land_verify_markers`) is
written right after a real land's commit exists on `root` but before the
post-land sweep runs (`_land_cmd._land_core`), and cleared immediately
after the sweep resolves (either outcome -- clean or reverted -- resolves
the pending window). A SIGTERM during the sweep itself now leaves this
marker behind instead of nothing.

`_land_cmd._report_stale_post_land_verify_markers` (read-only, never
mutates `root` -- the commit it names is already durably there either
way) runs at the start of every subsequent `_land_core` call (single-
ticket land and `_land_drain`'s loop alike): re-runs the same two
`LAND-PROOF` checks (`is_ancestor_of_main`, ticket state on main; shared
via new helper `_land_proof_checks`, factored out of `_print_land_proof`)
against any leftover marker, logs a `LAND-PROOF-RECOVERED:` line naming
the verified result, and clears the marker -- surfacing exactly what a
kill left ambiguous instead of leaving it silently unverified forever,
without ever blocking the NEW ticket this invocation is actually landing.

Deferred, disclosed: `LAND-PROOF`/`--finish` themselves were already
established as idempotent/safe-to-retry by playbook section 0 item 9 and
T-1175, so they are not part of this marker's covered window. The larger
Option A (every intermediate write self-describing) and Option B (a
separate resumable `--verify-only <sha>` CLI step) remain their own
design-doc-first follow-up if the sweep-specific gap closed here proves
insufficient in practice; a follow-up ticket has been filed for that
remaining design work rather than silently expanding this one's scope
(its real id will be assigned at land -- filed as a draft from this
worktree).

### Changed
```
 src/frob/tickets/_land.py         | 106 ++++++++++++++++-----
 src/frob/tickets/_land_git_ops.py |  49 +++++++---
 tests/test_ticket_land.py         | 164 +++++++++++++++++++++++++++++---
 tickets.md                        | 190 +++++++++++++++++++++++++++++++++++++-
 4 files changed, 451 insertions(+), 58 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_no_marker_is_a_silent_empty_result` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 514 warning(s), 791 waived
- error-findings: none (measured, zero errors)
