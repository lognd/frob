---
id: T-1419
title: 'The coverage stamp write does not survive: committed lock still asserts 81.2
  percent for a file measured at zero'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: T-1419's durability-check fix needs a matching test-file addition; narrowing
    scope to include it rather than leaving it uncovered
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_mismatch_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_match_succeeds
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_no_snapshot_skips_durability_check
designated_repro_test: null
acceptance:
- text: GIVEN a successful coverage stamp WHEN the resulting frob-coverage.lock.json
    is committed THEN its source_sha matches that run, not an earlier one
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_mismatch_exits_1
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_match_succeeds
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_no_snapshot_skips_durability_check
- text: GIVEN a module recorded at zero hits in that run report WHEN the committed
    lock is read THEN it records zero for that module
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_mismatch_exits_1
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_lock_source_sha_match_succeeds
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_no_snapshot_skips_durability_check
acceptance_amendments:
- op: remove
  index: 2
  old_text: GIVEN frob ticket land has generated or modified frob-coverage.lock.json
    during a land attempt WHEN the working tree is cleaned up THEN a freshly stamped
    lock is never reverted to an older committed copy -- corroborated independently
    by the T-1270 agent, which reported land leaving a stray lock diff in the root
    checkout that it resolved with git checkout on that file
  new_text: null
  reason: 'split to the follow-up ticket filed as T-draft-123eadc3 in this series:
    the revert guard lives in land-owned _land.py, outside T-1419''s declared scope
    (worktree agents may not touch land-owned files per playbook 4b); the stamp-verification
    half of the fix is delivered and bound'
  actor: logan
  at: '2026-08-02'
threat: null
component: null
---
T-1401 fixed the ratchet clamp so a genuine zero is recorded rather than carrying the prior value forward. That fix is correct and tested. But the committed lock is still wrong, because the stamp's write does not survive.

VERIFIED on main 2026-08-02, stating only what was measured:

- The COMMITTED frob-coverage.lock.json holds source_sha=de76e283 and src/frob/__main__.py = 81.2, confirmed with git show HEAD:frob-coverage.lock.json.
- A clean coverage run at 00:31 (exit 0, doctor healthy, no worker crashes) logged "stamp_coverage: stamped 860 file(s), source_sha=7454ba65".
- That run's own report, preserved at .frob/coverage.partial.xml, records src/frob/__main__.py at 0 of 133 lines hit. Likewise serve/_socketd.py 0 of 264 and serve/_leases.py 0 of 67.
- The working-tree lock is git-clean and identical to the committed version, with an mtime of 01:19 -- AFTER the 00:31 run.

So the stamp wrote source_sha=7454ba65 and something subsequently restored the committed de76e283 content. The net effect is that the ratchet floor in git never advances past de76e283, and it asserts 81.2 percent for a module the same repo measured at zero.

HYPOTHESIS, not verified, for whoever picks this up: frob-coverage.lock.json is a land-owned file (T-0731 -- a pre-commit hook refuses hand-edits, and frob ticket land lists it among the files it writes). A land, merge, or checkout between the stamp and now may be restoring the committed copy over the freshly stamped one. Confirm the mechanism before fixing; do not assume this one.

WHY IT MATTERS. The lock is the persisted ratchet floor: it is what survives the recipe's own frob clean, what delta and ratchet comparisons read, and what a coordinator inspects after coverage.xml is gone. A floor asserting 81.2 percent for a file with zero recorded hits will certify a genuine regression as fine. It also actively misleads diagnosis -- reading it as ground truth produced a wrong critical ticket earlier in this session (T-1398, since dropped), which is why playbook 6d now says to read coverage.xml instead.

This ticket is about DURABILITY, not the clamp. T-1401's carve-out is correct and should not be changed. The question is why a successful stamp's write is not what ends up committed.

Acceptance should be checkable end to end: run a coverage stamp, then confirm the committed lock's source_sha matches that run and that a module measured at zero in the report reads zero in the lock.