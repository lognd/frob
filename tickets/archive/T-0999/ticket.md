---
id: T-0999
title: 'EPIC: coordination churn reduction -- design out the drive''s recurring frictions
  (docs/audits/coordination-churn.md)'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/coordination-churn.md
- tests/test_ticket_land.py
- tests/unit/test_check_budget.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'epic close: evidence file per D-02 route'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_check_budget.py
  reason: 'epic close: second evidence file per D-02 route'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_persists_resume_state_for_deferred_groups
designated_repro_test: null
threat: null
component: null
---
User directive 2026-07-27: self-audit the drive for churn/tedious aspects and design them out. The audit doc ranks six recurring frictions with occurrence counts from ~160 landed closures; children implement the design-outs. Epic closes when every child lands and a subsequent multi-agent wave demonstrably runs without coordinator intervention for any of the six classes.