---
id: T-3144
title: 5 real failures in test_ticket_land.py masked by the FROB_WORKTREE leak (T-3123)
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_squash_command_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_final_commit_failure
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3123 fixed the FROB_WORKTREE cross-test env leak in tests/test_ticket_land.py
(autouse fixture in tests/conftest.py). With the leak contained, the file's
true failure floor is 5 of 330, all real and pre-existing, none
WorktreeLeaseViolation-shaped:

- TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- TestGitSubprocessFailures::test_squash_command_failure
- TestGitSubprocessFailures::test_final_commit_failure
- TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content

Measured 2026-08-27, series BZ: reproduced both in the full-file serial run
(uv run pytest -p no:xdist tests/test_ticket_land.py) and standalone (each
test run alone by node id, same failures, same assertions). Sample
(test_squash_command_failure): asserts result.is_err after monkeypatching
the --squash git spawn to fail, but land() returns Ok(...) instead --
either the monkeypatch's argv match no longer hits the real call site, or
land() stopped propagating that failure. Needs its own investigation; out
of scope for T-3123, which is the env-leak fix only.