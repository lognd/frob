---
id: T-2947
title: 'Land writes state=done and promotes drafts BEFORE the git merge succeeds:
  tip-drift leaves ledger-done with code absent from main'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_git_ops.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'T-2947: fix _refuse_drift_but_unstage to also restore working-tree content
    of modified TRACKED paths back to (post-drift) HEAD, not just unstage the index,
    so a drift-refused land can never leave a false done/promoted-draft state sitting
    on roots on-disk ticket files that no read of git history would show'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2947: fix _refuse_drift_but_unstage to also restore working-tree content
    of modified TRACKED paths back to (post-drift) HEAD, not just unstage the index,
    so a drift-refused land can never leave a false done/promoted-draft state sitting
    on roots on-disk ticket files that no read of git history would show'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'T-2947: fix _refuse_drift_but_unstage to also restore working-tree content
    of modified TRACKED paths back to post-drift HEAD, not just unstage the index,
    so a drift-refused land can never leave a false done or promoted-draft state sitting
    on roots on-disk ticket files that no git history read would show'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2947: fix _refuse_drift_but_unstage to also restore working-tree content
    of modified TRACKED paths back to post-drift HEAD, not just unstage the index,
    so a drift-refused land can never leave a false done or promoted-draft state sitting
    on roots on-disk ticket files that no git history read would show'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
