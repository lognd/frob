---
id: T-3938
title: REPEATED_FAILURE streak counter treats converging retries as stuck (apollo,
  second report)
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer apollo, 2026-09-06 (r9 wave), reporting the SAME complaint they filed at r4: the REPEATED_FAILURE streak counter counts converging retries as stuck. It fired on every multi-step land recovery they performed.

TWO INDEPENDENT REPORTS OF THE SAME BEHAVIOUR, wave apart, is corroboration -- this is not a one-off impression. It was not filed after r4, which is why it recurred.

THE DEFECT IS A MISSING DISTINCTION. A retry that makes progress and a retry that does not are different events, and the counter treats them identically -- it counts ATTEMPTS, not FAILURES TO CONVERGE. A multi-step land recovery is by construction a sequence of attempts that each get closer; penalising it is exactly backwards, because that sequence is the recovery working.

This is the silent-zero family seen from the other side: instead of a failed measurement rendering as a clean one, a SUCCEEDING process renders as a stuck one. The cost is the same -- the signal no longer distinguishes the two states, so the operator learns to ignore it.

WHAT TO DETERMINE FIRST (do not skip to the fix): what does the counter currently key on, and is there anything already available at that point that would let it tell converging from non-converging? A retry that changes the error, reduces the refusal count, or advances the land stage is converging. If no such signal exists at the call site, that absence is the real finding and should be reported before any counter arithmetic is touched.

DO NOT fix this by raising the threshold. A higher threshold delays the false positive rather than removing it, and it weakens the true positive it exists to catch.

MUST-FIRE FIXTURE: a genuinely stuck retry loop (identical failure, no progress) still trips the counter.
MUST-STAY-QUIET: a multi-step land recovery whose attempts converge does not.

ACCEPTANCE
- Converging and non-converging retries are distinguished by a real signal, not a tuned constant.
- Both fixtures committed -- the must-stay-quiet one is the point of the ticket, and without the must-fire one you cannot tell a fixed counter from a disabled one.