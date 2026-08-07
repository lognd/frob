---
id: T-0463
title: 'frob ticket land completeness: landing must bring the COMPLETE worktree changeset
  (tracked EDITS + UNTRACKED new files + deletions), with a post-land assertion that
  committed file set == worktree changeset -- git-diff-based surgical land silently
  drops new files (root cause of the T-0448 render.md loss)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandCompleteness::test_land_brings_tracked_edit_untracked_new_file_and_deletion
- tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing
designated_repro_test: null
threat: null
component: null
---
