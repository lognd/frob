---
id: T-3543
title: Fold the record-land-commit stub into the land itself (53 of last 300 commits)
state: done
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land_squash.py
- scripts/verify_lands.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_land_record_commit.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: the actual record-land-commit stub (_record_land_commit) and its readers
    live in these files, not the three declared -- _land.py/_land_finalize.py/_land_cmd.py
    only orchestrate the call
  actor: logan
  at: '2026-08-31'
- op: add
  glob: scripts/verify_lands.py
  reason: the actual record-land-commit stub (_record_land_commit) and its readers
    live in these files, not the three declared -- _land.py/_land_finalize.py/_land_cmd.py
    only orchestrate the call
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: the actual record-land-commit stub (_record_land_commit) and its readers
    live in these files, not the three declared -- _land.py/_land_finalize.py/_land_cmd.py
    only orchestrate the call
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/test_land_record_commit.py
  reason: add tests for derive_land_commit_by_grep + verify the removed follow-up
    commit stays removed
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/test_ticket_land.py
  reason: TestRecordLandCommit.test_records_land_commit_field_in_a_follow_up_commit
    directly encodes the pre-T-3543 land_commit-write behavior this ticket removes;
    must update in the same change
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: COV001/AFFECT001 need doc anchors for derive_land_commit_by_grep and load_land_commit's
    updated fallback behavior
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: COV001/AFFECT001 need doc anchors for derive_land_commit_by_grep and load_land_commit's
    updated fallback behavior
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_finds_the_squash_apply_commit_by_id_and_title_grep
- tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_returns_none_when_no_matching_commit_exists
- tests/test_ticket_land.py::TestRecordLandCommit::test_land_commit_is_derivable_with_no_follow_up_commit
- tests/test_ticket_land.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id
- tests/unit/test_coordinator_scripts.py::TestLoadLandCommit::test_returns_land_commit_for_a_landed_ticket
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
53 of the last 300 main commits are "chore(tickets): record land commit
for T-x" -- pure bookkeeping trailing every land as its own commit. Fold
it: the land-sha record is DERIVABLE (git log --grep "land T-<id>" -F)
or can be written as part of the land's own final commit (the out-of-tree
compose builds the commit; write the ledger field against the composed
tree before publish, or record the PARENT sha + "next commit" marker).
Pick the design that keeps `frob ticket show`/land-proof verification
working (they read the recorded sha today -- update their readers to
derive when absent). MUST-STAY-QUIET: land-proof (is_ancestor_of_main,
state_on_main) still verifies for old tickets with recorded shas AND new
tickets without them. ACCEPTANCE: a land produces exactly ONE trailing
ledger commit or zero, never a dedicated record-land stub.