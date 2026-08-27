---
id: T-3124
title: frob ticket new warns on scope overlap but never on duplicate titles or bodies
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_setters.py
  reason: declared scope named src/frob/tickets/_setters.py, which has no new_ticket/scope-overlap
    machinery at all; the actual scope-overlap check (_scope_overlap_warnings/_emit_scope_overlap_warnings)
    this ticket must generalize lives in src/frob/app/ticket_runner/_new.py
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: declared scope named src/frob/tickets/_setters.py, which has no new_ticket/scope-overlap
    machinery at all; the actual scope-overlap check (_scope_overlap_warnings/_emit_scope_overlap_warnings)
    this ticket must generalize lives in src/frob/app/ticket_runner/_new.py
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the measured exact-duplicate pair, the warn-not-refuse requirement,
    and the ledger-wide sweep ask
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 2814
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. T-3063 and T-3070 were both queued, both titled
"Wire evidence-reach classifier (T-3046) into frob check as a real WARN gate",
with BYTE-IDENTICAL bodies (10037 characters each). Two agents independently
filed the same ticket; neither `frob ticket new` nor any gate objected. I
dropped T-3070 by hand after noticing the pair while checking whether their
shared blocker had cleared.

WHAT THE TOOL DOES AND DOES NOT CHECK. `frob ticket new` DOES warn on scope
overlap -- it printed several "scope overlaps T-xxxx" warnings during this
session and those warnings are useful. It does NOT check the title or body
against existing tickets at all. So the near-miss detection exists for one
dimension (files) and is entirely absent for the dimension a human would
notice first (this is the same ticket).

WHY IT MATTERS MORE UNDER A FLEET. A single author rarely files the same
ticket twice; several agents working from the same measurements routinely
reach the same conclusion. This session filed roughly 35 tickets across a dozen
agents, and at least one exact duplicate got through -- plus two near-duplicates
from the TICK006 auto-recovery (T-3100/T-3103, dropped, see T-3108). Duplicates
are not merely untidy: two tickets on the same work can be dispatched to two
agents, who then collide on scope leases, or one can be "completed" while the
other rots, inflating both the queue and the done count.

WHAT IS WANTED -- WARN, DO NOT REFUSE. A duplicate is a judgement call and
sometimes two similar tickets are genuinely distinct work. The scope-overlap
warning is the right precedent and the right strength: print it, name the
candidate, let the author decide.
- At minimum: flag an EXACT title match against any non-terminal ticket.
- Better: flag high body similarity too. A byte-identical body is trivially
  detectable and would have caught this case outright.
- Do NOT reach for fuzzy semantic matching. Given this repo's standing
  directive to compare symbols rather than substrings, keep the check simple,
  deterministic and explainable -- exact title, and a cheap similarity ratio on
  the body, with the threshold stated.

ALSO WORTH REPORTING: sweep the current ledger for existing duplicate pairs by
the same criteria and report the count. If T-3063/T-3070 was the only one, that
is a useful result and the check is cheap insurance. If there are more, the
sweep is the more valuable half of this ticket.

ACCEPTANCE
- Filing a ticket whose title exactly matches a non-terminal ticket prints a
  warning naming the existing id. Must-fire fixture.
- Filing a genuinely new ticket prints nothing. Must-stay-quiet fixture.
- Filing is never REFUSED on similarity grounds -- warn only.
- The ledger-wide duplicate sweep is reported with a count and, if any are
  found, the pairs named.
