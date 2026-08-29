---
id: T-3414
title: 'DOC011: stale T-draft-ad5e921b citation in docs/modules/tickets.md'
state: done
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: the fix is a stale T-#### citation correction inside a documentation file
    (docs/modules/tickets.md), not a code-behavior change -- re-triaging from bug
    to docs so evidence can use the --evidence-cmd channel instead of forcing an artificial
    fail-then-pass pytest node
  actor: logan
  at: '2026-08-29'
evidence:
- cmd:bash -c 'uv run frob check --only docstatus 2>&1 | tee /tmp/doc011check.log;
  ! grep -q DOC011 /tmp/doc011check.log' exit=0 sha256=6f613c5c730e
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a9d9cd55f2023833fa01e222c3683ae2a1aeb61b
---
docs/modules/tickets.md:99 cites 'T-draft-ad5e921b', a draft id that was renumbered to T-3360 once the ticket was persisted (drafts get a real T-#### id on the next reconcile) -- the doc anchor never got updated to follow the rename, so DOC011 fires. Fix: replace the stale 'T-draft-ad5e921b' citation with 'T-3360'.