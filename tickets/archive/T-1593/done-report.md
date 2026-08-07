## Done report

Pure refactor to clear ARCH001's only 3 gate errors on main by splitting
each function along the seams the coordinator's dispatch called out (T-1518
stage seams for _land_core, decision-vs-run for _check_mutation_evidence,
drain-vs-per-entry for run_pending_sweep). Same call order, same
short-circuit/early-return semantics, same error values, same log lines --
verified by re-reading the extracted bodies against the original before/
after each split.

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_land_core
- src/frob/app/ticket_runner/_land_cmd.py::_land_core_prepare (new)
- src/frob/app/ticket_runner/_land_cmd.py::_land_core_start_baseline (new)
- src/frob/app/ticket_runner/_land_cmd.py::_land_core_invoke (new)
- src/frob/app/ticket_runner/_land_cmd.py::_land_core_finish_post_land (new)
- src/frob/tickets/_land.py::_check_mutation_evidence
- src/frob/tickets/_land.py::_mutation_evidence_sync_decision (new)
- src/frob/tickets/_land.py::_mutation_evidence_deferred (new)
- src/frob/tickets/_land.py::_mutation_evidence_synchronous (new)
- src/frob/tickets/_mutation_sweep_queue.py::run_pending_sweep
- src/frob/tickets/_mutation_sweep_queue.py::_load_pending_sweep_entries (new)
- src/frob/tickets/_mutation_sweep_queue.py::_process_pending_sweep_entries (new)
- src/frob/tickets/_mutation_sweep_queue.py::_process_one_pending_sweep_entry (new)
- src/frob/tickets/_mutation_sweep_queue.py::_save_pending_sweep_results (new)

First cut of _process_pending_sweep_entries came in at 61 lines -- still 1
over ARCH001's 60-line threshold -- so its per-entry loop body was split
out one seam further into _process_one_pending_sweep_entry. Re-checked
`frob check --only archgate --ticket T-1593 --json` after that second cut:
0 errors.

Evidence: (bound via `frob ticket evidence T-1593`)
tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_empty_queue_is_noop
tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_clean_finding_marks_swept_no_ticket_filed
tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_bug_kind_confirmatory_finding_files_ticket
tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_non_bug_confirmatory_finding_only_warns
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty
tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
tests/test_ticket_land.py::TestLand::test_real_land_lands

Measured test runs (all foreground, all exit 0):
- tests/test_ticket_land.py: 230 collected, 230 passed
- tests/unit/test_ticket_runner_land_release.py: 16 collected, 16 passed
- tests/unit/test_mutation_sweep_queue.py: 6 collected, 6 passed
- tests/test_tickets_mutation_evidence.py + tests/unit/test_ticket_runner_land_cmd_flags.py
  + tests/unit/test_app_runners_t0976_mutation_evidence.py: 36 collected,
  35 passed, 1 skipped, 0 failed
- Combined re-run of all six files together: exit 0, no failures, 3 skips
  total (xdist parallel run)
(one flaky, unrelated failure --
tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds
-- was seen on a single earlier standalone run and did NOT reproduce on the
immediate re-run of the same file, nor on the combined six-file run; not
touched by this ticket's scope)

Filed: none

Gates:
- `uv run ruff check` on all three touched files: clean (both PATH ruff and
  `uv run ruff`)
- `frob check --only archgate --ticket T-1593 --json`: gate:ARCH 0 errors,
  0 warnings, 61 waived (the 3 target functions no longer appear in the
  finding list at all)
- `frob check --land-parity`: clean -- 0 unscoped error(s), matches what
  the land sweep would see
- `git diff main --diff-filter=D --stat`: empty

Behavior unchanged: verified by direct comparison of each extracted
function's body against the original inline block it was cut from --
every helper is a byte-for-byte move of the original code (only comments/
docstrings added to name the new seam), call order between the new helpers
matches the original statement order exactly, and every early return /
`if result.is_err: ... return` / `Err(...)` / logged message is identical.
No new branches, no reordered side effects (the T-1463 baseline-thread
start/join and T-1523 marker write/clear still happen at exactly the same
points relative to the `land()` call and the post-land sweep).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 134 ++++++++++++++++++-----
 src/frob/tickets/_land.py                 | 107 +++++++++++++------
 src/frob/tickets/_mutation_sweep_queue.py | 171 +++++++++++++++++++-----------
 tickets.md                                |  14 ++-
 4 files changed, 305 insertions(+), 121 deletions(-)
```

### Evidence
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_empty_queue_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_clean_finding_marks_swept_no_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_bug_kind_confirmatory_finding_files_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_non_bug_confirmatory_finding_only_warns` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLand::test_real_land_lands` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 6209 warning(s), 798 waived
- error-findings: none (measured, zero errors)
