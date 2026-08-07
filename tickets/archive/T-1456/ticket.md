---
id: T-1456
title: land runs a post-land unscoped error sweep so relocation/waiver/format residue
  never reaches main
state: done
kind: feature
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_finalize.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: regression tests for the post-land unscoped sweep live in this existing
    land test-fixture module
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1456's new post-land unscoped sweep functions need frob:doc anchors; tickets.md
    is where frob ticket land is documented
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep
designated_repro_test: null
acceptance:
- text: GIVEN a land whose applied diff introduces an unscoped gate ERROR absent before
    the land WHEN land finishes THEN it either auto-fixed the residue or refused with
    the finding list, never left main's error floor regressed
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep
threat: null
component: null
---
Every wave this drive landed left small unscoped residue on main that the coordinator hand-fixed between lands: waivers that did not travel with relocated prose (T-1442's INV006/PII012), format drift, stale registry denominators, SELFAUDIT interface attrs for store blocks. Each was invisible to the land's --ticket-scoped verification and only surfaced in the next full frob check. Feature: after the squash-apply commit, land runs a bounded unscoped delta check (errors only, vs the pre-land baseline it already captures) and either auto-fixes Tier-A residue in a follow-up commit or refuses with the exact finding list, so main's error floor cannot regress silently at land time. The claim-divergence machinery (T-0754) already computes most of this; the gap is that it compares scoped, not unscoped-delta.