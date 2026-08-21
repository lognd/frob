---
id: T-2373
title: Burn ruff I001 (import-sort) warnings to zero, keep enforced
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
- src/frob/process/parsers/ruff.py
- tests/unit/test_parse.py
- src/frob/gates/__init__.py
- src/frob/gates/_arch.py
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_setters.py
- tests/unit/test_ticket_new_priority_inherit_t1960.py
- tests/unit/test_waive_audit_runner.py
- tests/unit/verify/test_attribution_module_scope.py
- tests/unit/verify/test_backpressure.py
- src/frob/gates/_waive.py
- docs/modules/process.md
- docs/modules/gates.md
evidence_scope:
- tests/unit/test_parse.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: epic rollup tracking I001 burn-down child tickets, batched
  per T-2359 precedent; no direct file scope of its own
scope_changes:
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_parse.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_ticket_new_priority_inherit_t1960.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_waive_audit_runner.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/verify/test_attribution_module_scope.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/verify/test_backpressure.py
  reason: 'final batch: 9 remaining I001 findings + severity promotion'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_waive.py
  reason: GATERULE001 registry entry + AFFECT001 doc closure for I001 promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/process.md
  reason: GATERULE001 registry entry + AFFECT001 doc closure for I001 promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/gates.md
  reason: DOCENUM001 member-list update for I001 registry addition
  actor: logan
  at: '2026-08-21'
evidence:
- tests/unit/test_parse.py::TestParseRuffText::test_severity_i001_is_error
- tests/unit/test_parse.py::TestParseRuffJson::test_i001_is_error
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence:
  - tests/unit/test_parse.py::TestParseRuffText::test_severity_i001_is_error
  - tests/unit/test_parse.py::TestParseRuffJson::test_i001_is_error
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence:
  - tests/unit/test_parse.py::TestParseRuffText::test_severity_i001_is_error
  - tests/unit/test_parse.py::TestParseRuffJson::test_i001_is_error
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (import ordering, auto-fixable via ruff --fix): 23 across codes I001.

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
