---
id: T-0856
title: 'land evidence re-verify: one failing test reports the ENTIRE evidence batch
  as failed; add per-id attribution + quarantine integration'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: New unit tests are needed for the T-0856 per-id batch-failure attribution
    fix (_reverify_failing_bucket_individually / _reverify_direct_pytest_individually
    / quarantine consultation) in src/frob/app/ticket_runner.py; adding to tests/unit/test_ticket_runner_land_release.py
    (existing precedent file covering ticket_runner land-adjacent CLI wiring).
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_only_the_genuinely_failing_id_is_excluded
- tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_quarantined_failing_id_still_counts_as_passing
- tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually::test_non_quarantined_failing_id_excluded
- tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingRoutesToIndividualReverify::test_batch_not_ok_falls_back_to_per_id_attribution
designated_repro_test: null
threat: null
component: null
---
Seen landing T-0588: its 36 evidence ids ran as ONE pytest batch; one documented order-dependent xdist flake failed and land reported every id as 'evidence did not pass post-merge' -- misattribution that sends the coordinator hunting through 36 green tests, and a single flaky test can permanently veto a land. Fix: parse per-test outcomes from the batch (or fall back to per-id reruns of only the failures), name ONLY the failing ids in the refusal, and consult frob.testing._stability quarantine (T-0575) so a quarantined flake does not veto -- blocked_by/cross-ref T-0635 which wires stability into frob test.