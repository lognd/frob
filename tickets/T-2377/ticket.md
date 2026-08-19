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
