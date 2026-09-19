---
id: T-4572
title: 'frob ticket land loses the compare-and-swap publish race to sibling ledger
  commits (ticket work/scope/accept mirrors) and refuses instead of re-merging and
  retrying: under 5+ agents every third land bounces with ''dev moved away from''
  and DirtyMain'
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_cas_ledger_retry.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cas_ledger_retry.py
  reason: new unleased test file for T-4572 CAS-retry fast path (test_land_compose.py/test_land_stage_flip.py
    both held by other in-progress tickets)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc anchors for the new commits_touch_only_ledger_paths/rebase_composed_commit_onto/_clean_root_on_refusal
    symbols (COV001)
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: coordinator repro
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 974
evidence:
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose
designated_repro_test: tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
acceptance:
- text: GIVEN the land branch advances by a ledger-only commit while a land composes
    WHEN the publish CAS misses THEN land re-merges and publishes on the next attempt
    without operator action.
  evidence:
  - tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
  - tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose
- text: GIVEN a refused land THEN git status in the root is clean.
  evidence:
  - tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Repro 2026-09-19: T-4553 and T-4555 lands each composed for 10+ minutes then refused with "dev moved away from <sha> while this land was composing (a sibling land published first), so the compare-and-swap publish was rejected" followed by "DirtyMain: root checkout has uncommitted changes". The mover was not a sibling land but agents' ledger mirrors (chore(tickets): mirror accept/scope ... from worktree), which T-3612 deliberately allows during a land.

Land should treat a CAS miss as a retry: re-merge the new tip into the staged squash, re-run only the cheap post-merge checks, and republish, bounded by N attempts; and it must leave the root clean on refusal (the DirtyMain that follows is land's own residue).

Acceptance:
GIVEN the land branch advances by a ledger-only commit while a land composes WHEN the publish CAS misses THEN land re-merges and publishes on the next attempt without operator action.
GIVEN a refused land THEN git status in the root is clean.