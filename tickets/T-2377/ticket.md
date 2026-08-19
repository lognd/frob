---
id: T-2377
title: Burn EXHAUST002/EXHAUST003 WARN gates to zero, then promote to error
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
blocked_by:
- T-2543
- T-2568
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_exhaustive_handling.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_normalized.py
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/arch/_python.py
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/arch/_mayraise.py
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/arch.md
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_arch.py
  reason: 'EXHAUST002/003 burn-down: the may-raise resolver, its python adapter, the
    exhaustiveness gate that consumes it, their docs and tests'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/arch/_normalized.py
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/arch/_python.py
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/arch/_mayraise.py
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/modules/arch.md
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/unit/test_arch.py
  reason: 'moved to T-2539: the resolver false-positive fixes found during this burn-down
    are their own bug ticket; T-2377 re-scopes once the remaining findings are triaged'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'T-2377 is now the PROMOTION ticket only: its detector-precision half moved
    to T-2539 (landed) and T-2552 (landed), and its remaining false-positive half
    is T-2543, which now blocks it. Scoped to the two files that carry the WARN->ERROR
    flip -- the gate module''s Severity constants and the gate catalog''s own text
    -- deliberately NOT to the ~30 finding-bearing source files, because which of
    those need a real change is exactly what T-2543''s Class A decision determines.
    Widen this scope only after that decision lands, so this ticket stays disjoint
    from sibling children of T-0969 in the meantime.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-2377 is now the PROMOTION ticket only: its detector-precision half moved
    to T-2539 (landed) and T-2552 (landed), and its remaining false-positive half
    is T-2543, which now blocks it. Scoped to the two files that carry the WARN->ERROR
    flip -- the gate module''s Severity constants and the gate catalog''s own text
    -- deliberately NOT to the ~30 finding-bearing source files, because which of
    those need a real change is exactly what T-2543''s Class A decision determines.
    Widen this scope only after that decision lands, so this ticket stays disjoint
    from sibling children of T-0969 in the meantime.

    '
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'A4 (the coordinator-authorized rule split) edits the gate module''s violation
    emission and the gate catalog that documents the new rule id, so both globs move
    here for the duration of this ticket. They return to T-2377 -- which is blocked_by
    T-2543 and therefore not being worked in the meantime -- once this lands.

    '
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/modules/gates.md
  reason: 'A4 (the coordinator-authorized rule split) edits the gate module''s violation
    emission and the gate catalog that documents the new rule id, so both globs move
    here for the duration of this ticket. They return to T-2377 -- which is blocked_by
    T-2543 and therefore not being worked in the meantime -- once this lands.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'Returned from T-2543 now that A2+A4 have landed. These two files are the
    promotion surface: the gate module carries the Severity constants for the WARN->ERROR
    flip and the gate catalog carries the text that documents it. EXHAUST002 now stands
    at 8 findings, all of them the single guard-predicate class filed as T-2568, so
    that ticket is the last thing between this one and its EXHAUST002 half. EXHAUST003
    is NOT to be promoted -- held for the user.

    '
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: 'Returned from T-2543 now that A2+A4 have landed. These two files are the
    promotion surface: the gate module carries the Severity constants for the WARN->ERROR
    flip and the gate catalog carries the text that documents it. EXHAUST002 now stands
    at 8 findings, all of them the single guard-predicate class filed as T-2568, so
    that ticket is the last thing between this one and its EXHAUST002 half. EXHAUST003
    is NOT to be promoted -- held for the user.

    '
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'owner decision: mint EXHAUST004 approved, promote to ERROR after burn-down'
  actor: logan
  at: '2026-08-19'
  old_length: 1338
  new_length: 3834
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (exhaustiveness checks (unhandled enum/union arms)): 179 across codes EXHAUST002, EXHAUST003.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.



## OWNER DECISION (2026-08-19): mint EXHAUST004, promote to ERROR

The repo owner has decided both open questions on this ticket:

1. **Minting a new rule id is APPROVED.** EXHAUST004 may be created as
   part of the split, and it belongs in the v1.0.0 gate surface. Do not
   defer it to a later milestone.
2. **Promotion to ERROR is the preferred outcome**, not a permanent WARN.
   EXHAUST003 (and EXHAUST002) should end as ERROR-severity gates once
   the burn-down reaches zero.

So the sequence stands as this ticket's title describes: burn to zero
FIRST, promote SECOND. Do not promote while findings remain -- an ERROR
gate that fires on landing main blocks every agent, and this repo has
already paid for that shape (a single unused import raised quarantine and
forced fleet-wide synchronous lands for hours).

### The 26 waivers

The split surfaces ~26 waivers across ~20 files that need retargeting.
Retarget them as part of this work. Do NOT bulk-rewrite them: T-2612
audited 12 expired-premise waivers and found 9 of them hiding REAL owed
work, not merely stale text. Expect a similar split here. For each, check
whether the finding still fires once retargeted; if the underlying work was
never done, do it or file a ticket, but do not re-word a reason to keep a
live finding suppressed.

### Still blocked

This ticket is `blocked_by` T-2568 (queued as of this decision), so it is
not yet startable. The decision is recorded now so the work is unambiguous
the moment T-2568 lands.

NOTE for whoever picks this up: this ticket previously leaked a write lease
on `docs/modules/gates.md` for nine hours -- in-progress, blocked, worktree
removed by hand. It blocked T-2613 and forced four other tickets to skip
Tier-A doc fixes. It has been requeued. If you start it and then find
yourself blocked again, REQUEUE IT rather than leaving it in-progress; a
blocked ticket must not hold a lease it cannot use. T-2654 is adding a
check that flags exactly this shape.

### Positive controls, both directions

- after the burn-down, EXHAUST002/EXHAUST003 report ZERO findings on an
  unscoped `frob check`, measured and stated against a denominator
- promoted to ERROR, a deliberately planted violation FAILS the gate
- a legitimate, correctly-waived case still passes -- without this the
  promotion is indistinguishable from a gate that always fires
- EXHAUST004 fires on the case it was minted to catch, and does NOT fire
  on the cases EXHAUST002/003 already cover (no double-reporting)