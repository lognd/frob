---
id: T-1463
title: frob ticket land now exceeds the 540s foreground budget; sweep and checks need
  memoized reuse
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land_finalize.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep
designated_repro_test: null
acceptance:
- text: GIVEN a typical single-ticket land WHEN run foreground THEN it completes inside
    the documented budget with the post-land sweep actually executed
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
  - tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep
threat: null
component: null
---
After T-1456 (post-land unscoped error sweep) and the growing gate set, a single frob ticket land runs multiple near-full frob check invocations (pre-land baseline capture, post-merge claim re-verification, post-land sweep) and now regularly exceeds the playbook's 540s foreground budget -- two lands on 2026-08-02 died with exit 143 during post-land cleanup (the land itself committed; the sweep never ran, letting residue through in exactly the way T-1456 was built to stop). Fix directions: reuse one shared check invocation's results across the land phases (the T-1346 gate cache should make back-to-back runs cheap -- measure why it does not), run the baseline capture concurrently with the pre-land merge, and/or split the sweep into its own post-land verb the coordinator can run in background. The foreground-budget hook and playbook section 3b guidance also need updating to whatever the fixed land's real worst case is.