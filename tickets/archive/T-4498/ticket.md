---
id: T-4498
title: land's merge-dev step resolves a conflicting design/frob.strata and ratchet
  lock toward the target branch, silently dropping the worktree's capability declarations
state: done
kind: bug
origin: agent
created: '2026-09-15'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land.py
- tests/unit/test_land_merge_conflict_drop.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'T-4498 amendment(c): new test file execs git subprocesses and writes/reads
    fixture files, needs testsuite via-list entry'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: 'T-4498 amendment(c): bump accepted_count alongside the new via-list entry'
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
designated_repro_test: null
acceptance:
- text: GIVEN a worktree whose design/frob.strata edit conflicts textually with the
    target branch's newer edit of the same via-list line WHEN the land merges the
    target branch into the worktree THEN it refuses with a named conflict (file, both
    tickets) instead of silently keeping the target branch's side
  evidence:
  - tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 on the T-4492 land: worktree commit 0294ab436 added tests/unit/test_lifecycle_work_base.py to the testsuite exec and fs.write via-lists (design/frob.strata) and bumped docs/design/registry/capability-via-ratchet.lock.json 307->308 and 521->522. The land's 'merge dev into worktree for landing T-4492' commit (afcd60105) resolved both files to dev's side (T-4491 had edited the same lines, merge-base 02c20c18c) with no conflict reported, and the subsequent self-audit refused the land with the very SELFAUDIT001 findings the dropped edit declared. A conflict on a non-ledger file must surface as a refusal naming both sides; only tickets/** may be auto-resolved by the ledger merge driver.