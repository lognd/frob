---
id: T-5175
title: 'frob ticket attach --remove PATH: first-class attachment removal with ledger
  record cleanup'
state: dropped
kind: feature
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_attach.py
- src/frob/tickets/_attach.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: given a ticket with one attachment, when frob ticket attach ID --remove PATH
    runs, then the file is gone, the record is gone, and the ledger commit is made
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20: no verb removes an attachment; the owner asked for research attachments to be removed and the only path was a script over the attachments: frontmatter block plus git rm, i.e. a hand-edit of the ledger the ticket-ledger-gotchas lesson forbids. Add --remove PATH (and --remove-all) that deletes the file, drops the Attachment record, and auto-commits like attach does; refuse when the path is referenced by a done-report.

## Drop reason
- 2026-09-21: duplicate of T-5172: stale worktree copy of T-draft-1b1cebcb re-promoted before the dev merge renamed it away
