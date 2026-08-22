---
id: T-2834
title: Split frob.tickets._setters's sprint/flow analytics family into _flow.py
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- src/frob/tickets/_flow.py
evidence_scope:
- tests/test_tickets_velocity.py
- tests/test_tickets_tiers.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history
- tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob.tickets._setters.py (1573 lines) has a real, investigated seam: the sprint/flow analytics family (sprint_view, sprint_velocity, ticket_flow, and their git-history-mining helpers -- _ledger_commit_history/_blob_at/_mine_done_transitions*/_load_flow_ticket_universe/_count_filed_by_day/_count_landed_by_day/_build_flow_rows/_median_cycle_days, roughly 440 lines) is a distinct concern from the single-field setter family (set_priority/set_kind/set_tier/set_parent/set_body/etc) the rest of the module holds -- the setters mutate one ticket's field, the flow family mines git history across the whole queue to report burn-down/velocity.

Extraction into a new frob.tickets._flow module was rejected in T-2822 (LARGE001 batch 2) purely on scope grounds:

1. A new source file is not covered by T-2822's enumerated file-list scope (no glob to grow into).
2. frob.tickets.__init__ re-exports sprint_velocity/sprint_view/ticket_flow at the package level for tests/app/ticket_runner/_mutate.py + _query.py's `from frob.tickets import ...` call sites -- __init__.py was outside T-2822's scope to amend if the re-export path needed touching (it likely does not, if _setters.py keeps importing the three names back from the new module and re-exporting them, mirroring the pattern frob.tickets._land uses for its own split-out siblings -- but this needs verifying at land time by whoever picks this up).

This is a legitimate real split (not a T-1651-style waive candidate) -- scope it explicitly and land it as its own ticket.