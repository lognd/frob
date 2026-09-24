---
id: T-5518
title: 'land: rebuild stale natives after squash-apply, before post-merge evidence
  re-verification'
state: done
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-342a3548
branch: t-draft-342a3548
scope:
- src/frob/tickets/_land_verify.py
- tests/unit/tickets/test_land_verify*.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: rebuild stale worktree natives before post-merge evidence re-verification
    (T-1213 second call site)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/tickets/test_land_verify*.py
  reason: rebuild stale worktree natives before post-merge evidence re-verification
    (T-1213 second call site)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: rebuild stale worktree natives before post-merge evidence re-verification
    (T-1213 second call site)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_land_verify_natives.py::TestRebuildStaleWorktreeNatives::test_stale_fake_native_triggers_rebuild
- tests/unit/test_land_verify_natives.py::TestRebuildStaleWorktreeNatives::test_fresh_natives_stay_quiet
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-24 (T-3010, two land attempts): the T-1213 stale-natives auto-rebuild runs in the pre-squash gates phase. The squash-apply then brings the ticket's Rust changes (strata-core/src/lib.rs, graph/vmodel/closure.rs) into the tree, and the post-merge evidence re-verification runs against a strata_core extension built before that, so every evidence test importing the new PyO3 export failed "individually" and the land was refused. The same tests pass in the worktree after frob natives build with no source change; the dry-run was clean because it stops before squash-apply. A pre-land natives rebuild in the worktree (coordinator hygiene) did not help, so the extension used at evidence time is not the worktree's freshly built one.

Fix: after squash-apply and before evidence re-verification, run the stale-natives check against the squash-applied tree and rebuild into the interpreter the evidence run will use (same T-1213 detector, second call site), and log which interpreter and extension file the evidence run resolved. Positive control: a ticket adding a PyO3 export plus an evidence test that imports it lands on the first attempt.