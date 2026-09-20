---
id: T-3825
title: 'F-020: frob check --only sys SELFAUDIT001/SYS103 reports files as unbound
  that ARE bound by a multi-glob code= line (or stale .frob design cache) -- gate
  cannot go green; fix multi-glob code binding / cache freshness'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: T-4665
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
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
  reason: '2026-09-19: SF-17 in the STRATA friction audit; joins story B of epic T-4662
    -- a false positive that blocks green and whose stale-cache half interacts with
    T-4669'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v1.1.0
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-17''s evidence row verbatim plus the instruction
    to establish which of the two named causes (matcher vs stale design cache) is
    live before fixing either, and to coordinate the cache half with T-4669 instead
    of adding a second invalidation scheme'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1682
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## SF-17 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-17, evidence table row verbatim:

| SF-17 | SYS103/SELFAUDIT001 false-positives on multi-glob `code=` bindings; gate cannot go green | tickets/T-3825/ticket.md (F-020, queued) | blocks green | MEDIUM |

And verbatim from the SF-14/15/16/17 section:
"T-3825 (F-020): 'frob check --only sys SELFAUDIT001/SYS103 reports files as
unbound that ARE bound by a multi-glob code= line (or stale .frob design cache)
-- gate cannot go green'. Queued. Fix surface: gate (matcher + cache freshness)."

NOW A CHILD OF T-4665 (story B of epic T-4662). Two notes for whoever takes it:

1. The ticket names TWO candidate causes -- a matcher bug on multi-glob `code=`
   lines, and a STALE .frob design cache. Per
   memory/verify-premise-before-filing.md, establish which one is live at HEAD
   before fixing either; a matcher fix that is really a cache-staleness bug will
   regress the moment the cache goes stale again.
2. The cache half interacts directly with T-4669 (SF-04/SF-20), which adds a
   digest-keyed cache for capability_via_site_counts and load_design_ids. That
   ticket's second acceptance criterion is specifically that a stale hit must be
   impossible to mistake for a clean scan. If the stale-cache cause is the live
   one here, coordinate with T-4669 rather than adding a second cache-freshness
   mechanism -- two invalidation schemes over the same data is the desync this
   epic exists to remove.

"Gate cannot go green" is the cost line: this is a false positive that cannot be
worked around, only waived, which is how a gate loses its meaning.
