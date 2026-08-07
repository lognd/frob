---
id: T-1513
title: 'post-land Tier-A cleanup commit fails: git add -A stages land-owned uv.lock
  and pre-commit hook refuses'
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_fix_commit_stages_only_touched_paths_not_git_add_dash_a
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
designated_repro_test: null
threat: null
component: null
---
In _sweep_apply_tier_a_and_commit (src/frob/app/ticket_runner/_land_cmd.py), the T-1456 autofix-retry phase runs git add -A + plain git commit. add -A stages the perpetually-dirty uv.lock (and any other land-owned file), the T-0731 pre-commit hook refuses, the fix stays uncommitted ('N left uncommitted'), the re-scan still sees the errors, and the land reverts -- observed on every refused land 2026-08-03/04. Fix: stage only the files the Tier-A engine actually touched, and run the commit with FROB_LAND_INTERNAL=1 like land's other internal commits. Also consider logging the git stderr on commit failure (it was silent).