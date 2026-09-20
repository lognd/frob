## Done report

All six named SIGKILL/SIGTERM-victim helpers switched multiprocessing get_context from fork to spawn (all targets are module-level, importable functions with picklable args, so no cost); no production code path forks a threaded process (git grep found only comments/detector regexes in src/frob/arch/_concurrency.py, no live fork call). The DeprecationWarning is py3.12+-only so this py3.11 worktree cannot reproduce it under -W error -- recorded as a BUG002 waiver; fix verified by inspection (git grep -n get_context confirms no remaining fork context in the six named files) and will confirm clean on the next macOS CI push.

### Changed
```
 tests/ticket_land_suite/test_verify_reset.py | 28 ++++++++++++++++++++++++----
 tests/unit/test_fix_engine_journal.py        |  8 ++++++--
 tests/unit/test_land_finish_guard.py         |  7 ++++++-
 tests/unit/test_land_lock_liveness.py        | 12 +++++++++---
 tickets/T-4452/ticket.md                     | 19 +++++++++++++++++++
 5 files changed, 64 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm::test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content` (pytest node id, verified passing when recorded)
- `tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournalSigkillSubprocess::test_sigkilled_journal_writer_is_detected_and_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 4800 warning(s), 964 waived
- error-findings: TICK004@tickets.md
