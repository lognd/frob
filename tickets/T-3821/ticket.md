---
id: T-3821
title: 'F-016: design-first repo gets SYS101 (declared-never-observed) for planned
  capabilities -- need a milestone/planned marker so SYS101 stays quiet until the
  owning component milestone is active (relates to T-3004 sec 6)'
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: T-4665
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
  new_value: T-4665
  reason: '2026-09-19: SF-15 in the STRATA friction audit; joins story B of epic T-4662
    (gate signal and consumer-reported false positives)'
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-15''s evidence row verbatim plus the constraint
    that any grammar-surface part of this fix must be split out as a DECISION under
    T-4667, since the owner is rethinking strata grammar'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1687
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## SF-15 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-15, evidence table row verbatim:

| SF-15 | SYS101 fires on design-first repos: you cannot declare a capability before you implement it | tickets/T-3821/ticket.md (F-016, queued, medium) | every consumer design-first repo | MEDIUM |

And from the SF-14/15/16/17 section verbatim:
"T-3821 (F-016): 'design-first repo gets SYS101 (declared-never-observed) for
planned capabilities -- need a milestone/planned marker'. Queued. Fix surface:
grammar (a planned/milestone marker) + gate."
"These four are all `origin: human`, all filed from consumer repos, all
`priority: medium`, all parked on milestone v1.1.0 -- i.e. the friction the
outside world reports about SYS is uniformly deferred."

NOW A CHILD OF T-4665 (story B of epic T-4662), with one caveat the implementer
must honour: the audit records this ticket's fix surface as GRAMMAR (a
planned/milestone marker) PLUS gate. The owner is personally rethinking strata
grammar and semantics, and T-4662 files every grammar-surface finding as a
DECISION rather than as work. So if the chosen fix here requires a new
declaration marker, split that part out as a DECISION under T-4667 and build
only the gate side. A gate-only fix is plausible -- SYS101 could defer
"declared-never-observed" for a capability whose node carries an existing
milestone attribute -- and that is the option to explore first.

Read alongside T-4672 (SF-01): 614,294 telemetry rule fires contain ZERO SYS
ids, so nothing on record says how often SYS101 actually fires in consumer
repos. T-4672 is the instrumentation that would answer it.
