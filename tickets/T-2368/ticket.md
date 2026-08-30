---
id: T-2368
title: Burn INV/NEGEXIST/WALK/PLACE/PII/DEAD/LANG WARN gates to zero, then promote
  to error
state: queued
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
- tests/test_gates.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'PLACE001 burn-down: fix ambiguous frob:ticket directive placement in these
    two test files'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'PLACE001 burn-down: fix ambiguous frob:ticket directive placement in these
    two test files'
  actor: logan
  at: '2026-08-30'
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
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage, no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding counts, this family:
- INV003 + INV004: 10
- NEGEXIST001: 13
- WALK001: 3
- PLACE001: 2
- PII011: 2
- DEAD001: 5
- LANG003: 3
Total: 38 findings across ~71 distinct files (shared denominator with the REF/REG sibling child -- see that ticket for the split).

Grouped together because each individual code's count is too small to justify its own ticket, but they are otherwise unrelated gate families (invariant coverage, negative-existence checks, unpruned traversal, placement, PII, dead code, language conformance) -- read each finding's own gate docs (docs/modules/gates.md) before fixing, do not assume a shared fix.

Closure is two-part per the epic (T-0969): (1) zero findings for every code above, verified via `uv run frob check --json --budget 500 | python3 scripts/check_summary.py` reporting 0 for INV003/INV004/NEGEXIST001/WALK001/PLACE001/PII011/DEAD001/LANG003, AND (2) each promoted from warning to error tier in the gate definition (grep the gate module for its severity constant) -- a burn-down that stops at zero and leaves the gate advisory lets the debt silently reaccumulate.

Narrow `scope` to the actual files touched once you've run the gate and see which ~71 files are involved; do not take a broad blanket scope.
