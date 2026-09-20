---
id: T-4666
title: 'Story C: assumptions and claims as-implemented -- wire the overdue-assume
  verdict before the 2026-10-15 cliff'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4662
tier: story
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: story container under T-4662; the disjoint
  scopes live on its leaves'
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given _models.py:589, docs/strata/evidence.md:117 and docs/strata/charter.md:4
    all describe overdue assumes as gate failures while _claims.py:654 only logs a
    warning and returns Verdict.ASSUMED, when this story closes, then an assume with
    a past review date produces a gate finding proven by a positive-control test,
    and all four artifacts agree.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Story C of T-4662. Covers SF-07 and SF-23.

THE MEASURED PROBLEM
The assumption ledger's central rule is documented as enforced, asserted as
enforced in the data model's own comment, and is not enforced anywhere.

SF-07 (HIGH), every line re-verified by the planner at HEAD:
- src/frob/strata/_models.py:589
    review: str | None = None  # ISO date; overdue assumes are gate failures
- docs/strata/evidence.md:117
    "an overdue review date is a gate failure"
- src/frob/strata/_claims.py:654-655 (_eval_assumed) is the ENTIRE enforcement:
    _log.warning("assume %s review overdue (%s)", claim.id, claim.review)
    detail += f"; review overdue since {claim.review}"
  and the function returns Verdict.ASSUMED. Nothing converts that to a
  Violation. `git grep overdue -- src/frob` returns only those two lines.
- docs/strata/charter.md:4 already concedes it inside an INV003 waiver reason:
  "Law 3's 'overdue assumptions are gate failures' specifically is NOT yet wired
  into frob check (evaluate_claims flags an overdue assume in its detail text
  but stays verdict=ASSUMED, not a gate error) -- that gap is real design debt".

THE CLIFF: all 33 assumes in design/frob.strata carry review "2026-10-15". On
2026-10-16 the TCB of frob's own security model silently expires and the gate
stays green. That is 26 days from the audit date. This is why story C is high
priority and not deferrable behind the grammar rethink: wiring a verdict that
three artifacts already claim exists is not a semantics change, it is closing
the gap between the code and its own comment.

SF-23 (LOW, historical): archive/T-0164 already named the class -- "COV002
demands per-declaration frob:ticket edges inside .strata files -- boilerplate".
Cited so this epic knows the per-declaration-directive boilerplate pattern
predates the current model.

ACCEPTANCE
An assume with a past review date produces a gate finding, proven by a test that
fails at HEAD; and docs/strata/evidence.md, charter.md and _models.py:589 all
agree with the implementation afterwards.
