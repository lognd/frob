---
id: T-2009
title: Deferred post-land sweep attributes a finding to whichever ticket's sweep fires
  next, not the land that introduced it
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2009: attribution mismatch lives entirely in run_deferred_post_land_sweep/_file_regression_ticket''s
    title/body construction in this module; the fix and its regression test both live
    here'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2009: attribution mismatch lives entirely in run_deferred_post_land_sweep/_file_regression_ticket''s
    title/body construction in this module; the fix and its regression test both live
    here'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_absent_is_none
- tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_read_baseline_commit_round_trips
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_single_land_in_range
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_multiple_lands_in_range_oldest_first
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_land_commits_are_ignored
- tests/unit/test_rapid_sweep.py::TestLandIdsBetween::test_non_repo_returns_empty_list
- tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_non_repo_falls_back_to_the_given_commit
- tests/unit/test_rapid_sweep.py::TestResolveActualHead::test_real_repo_resolves_the_true_head
- tests/unit/test_rapid_sweep.py::TestDeferredSweepMultiLandAttribution::test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
