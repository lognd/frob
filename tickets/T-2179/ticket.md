---
id: T-2179
title: fleet_status.py::worktrees_touching_ticket reports ledger-only churn as 'already
  implemented' (T-2172 follow-up)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: tests + doc anchors for the scope-aware worktrees_touching_ticket fix
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: tests + doc anchors for the scope-aware worktrees_touching_ticket fix
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found by the coordinator using `--ticket` (T-2172's own new flag) for real
dispatch decisions: `worktrees_touching_ticket` reports ANY worktree branch
with an unlanded commit touching `tickets/<id>/` as "already implemented",
with no distinction between:

- a branch that touched files in the ticket's own declared SCOPE (genuine
  implementation work -- should report loudly)
- a branch that touched ONLY `tickets/<id>/**` itself (a ledger-only edit --
  id-collision renumbering churn, a scope narrowing, a Done report commit
  on a ticket that was later abandoned/renumbered away -- not implementation
  at all)

Real incident: `--ticket T-2114` printed `ALREADY IMPLEMENTED on: t-2071,
t-2099, t-2105, t-2107, t-2109, t-2110, t2049-series` -- seven branches, none
of which actually implemented T-2114. T-2114 briefly collided with a
different ticket id before being renumbered to T-2140; every one of those
branches touched `tickets/T-2114/ticket.md` during that collision-recovery
churn, never the ticket's own declared scope. A coordinator trusting this
line would skip real work believing it was already done -- worse than
printing nothing, since a false "already implemented" is exactly the kind
of wrong answer that gets trusted without re-checking.

Fix: `worktrees_touching_ticket` (or `ticket_readiness`, whichever owns the
distinction) should only report a worktree as "already implemented" when
its unlanded commits touch a file matching the ticket's OWN declared scope
globs (from `ticket_frontmatter_on_main`, same source `ticket_readiness`
already reads) -- not merely `tickets/<id>/**`. A branch that touched only
the ticket's own ledger path should report as ledger-only (or not at all),
never as implementation evidence.

Filed as a follow-up to T-2172 per the coordinator's explicit instruction,
not folded into T-2167/T-2171/T-2174 (a distinct defect in a tool
coordinators now rely on for real dispatch decisions).