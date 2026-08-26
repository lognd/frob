---
id: T-2372
title: Burn TICK004/TICK007/TICK011 WARN gates to zero, then promote to error
state: in-progress
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tickets/archive/T-2556/done-report.md
- tickets/archive/T-2653/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: TICK004/TICK007/TICK011 severity promotion lives in this gate module
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2556/done-report.md
  reason: 'TICK011 remediation: repair the two archived Done reports whose disclosures
    needed a nearby citation/no-ticket-needed marker (see gate-code fix in the same
    ticket for why the other 7 were bare-word false positives, not real gaps)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2653/done-report.md
  reason: 'TICK011 remediation: repair the two archived Done reports whose disclosures
    needed a nearby citation/no-ticket-needed marker (see gate-code fix in the same
    ticket for why the other 7 were bare-word false positives, not real gaps)'
  actor: logan
  at: '2026-08-26'
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

WARN-tier finding count, this family (ledger-hygiene checks (rotting tickets, disclosed-cut citations)): 17 across codes TICK004, TICK007, TICK011.

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
