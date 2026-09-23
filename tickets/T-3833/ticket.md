---
id: T-3833
title: 'F-028: SYS111 ratchet fires the moment a via-list is INTRODUCED (ceiling 0)
  in the same commit that creates the design'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: T-4664
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4664
  reason: '2026-09-19: SF-14 in the STRATA friction audit; joins story A of epic T-4662
    because it is the degenerate case (ceiling 0) of the same hand-committed-ceiling
    race T-4671 fixes'
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-14''s measured evidence from scratchpad/STRATA-FRICTION.md
    as this ticket joins story A (T-4664) of epic T-4662; records that SF-14 is the
    degenerate case of T-4671''s ratchet race and must not be fixed independently'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1476
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## SF-14 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Re-measured at HEAD c8f56ef10 and recorded in scratchpad/STRATA-FRICTION.md as
SF-14, evidence table row verbatim:

| SF-14 | SYS111 fires on introduction (ceiling 0) -- the design and its ceiling cannot be committed in one change | tickets/T-3833/ticket.md (F-028, queued, medium, milestone v1.1.0) | every new node/grant | MEDIUM |

Why this ticket is now a child of T-4664 (story A of epic T-4662) rather than a
standalone consumer report: SF-14 is one end of the same mechanism story A
exists to fix. The other end is SF-13, the ratchet-race regression chain
(T-4495 -> T-4563 -> T-4596 -> T-4607 -> T-4633 -> T-draft-a62505d4), now filed
as T-4671 "derive the SYS111 ceiling instead of committing it". Both are the
same root cause: a number committed BY HAND against a moving branch. Ceiling 0
on introduction is the degenerate case of that race -- there is no prior
committed number to bump, so the first commit is always wrong.

The audit also recorded, as SF-14/15/16/17's shared framing: these four are all
`origin: human`, all filed from CONSUMER repos, all `priority: medium`, all
parked on milestone v1.1.0 -- i.e. the friction the outside world reports about
SYS is uniformly deferred. That pattern, not this ticket alone, is what story B
(T-4665) and story A exist to break.

Do not fix SF-14 independently of T-4671; a fix that special-cases ceiling 0
leaves the general race intact.
