---
id: T-6586
title: 'frob ticket new --points N is silently dropped: the ticket is written with
  points null'
state: dropped
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 949
  new_length: 1055
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the project-hullbreach session (2026-09-26) while importing 116
Jira items. Reproduced by the coordinator on BOTH the global tool
(0.531.1.dev338) and the working tree (0.531.1.dev344) in a fresh
python-tool scaffold:
    frob ticket new --title "points repro" --kind feature --tier ticket --points 3 --scope src/ --no-commit
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->    -> created T-0001, tickets/T-0001/ticket.md has `points: null`
No warning is printed (the "filed with no --points" WARN does not fire
either, so `spec.points` is set at validation time and lost before the
write). `frob ticket points <id> N` afterwards does persist. Trace the value
from `cfg.ticket_points` (src/frob/app/ticket_runner/_new.py) through
`new_ticket`/`_new_renumber.py` to the ticket.md writer and fix the drop.
Positive control: a test that files with --points 3 and asserts the
written ticket.md carries `points: 3`; the same test must fail on the
current tree. Designated repro: that test.

## Drop reason
- 2026-09-26: duplicate of T-5815 (ticket new --points not persisted), which landed on dev 430899e128 on 2026-09-26
