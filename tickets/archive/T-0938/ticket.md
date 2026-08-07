---
id: T-0938
title: sprint velocity/burndown derived from ledger state-transition history
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: medium
blocked_by:
- T-0715
parent: T-0715
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets_velocity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'SCOPE002 (frob check --only scope) fires repo-wide for T-0938''s original

    scope (src/frob/tickets/** only): every pre-existing public symbol in

    src/frob/tickets/__init__.py that carries a frob:doc anchor into

    docs/modules/tickets.md trips it, because that doc file was never in

    scope. Widening scope to include the doc file (where sprint_velocity''s

    new public API/data-model entries genuinely belong documented anyway)

    and the new test file (tests/test_tickets_velocity.py, required by

    SCOPE001) resolves both structurally instead of waiving 40+ individual

    findings.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_velocity.py
  reason: 'SCOPE002 (frob check --only scope) fires repo-wide for T-0938''s original

    scope (src/frob/tickets/** only): every pre-existing public symbol in

    src/frob/tickets/__init__.py that carries a frob:doc anchor into

    docs/modules/tickets.md trips it, because that doc file was never in

    scope. Widening scope to include the doc file (where sprint_velocity''s

    new public API/data-model entries genuinely belong documented anyway)

    and the new test file (tests/test_tickets_velocity.py, required by

    SCOPE001) resolves both structurally instead of waiving 40+ individual

    findings.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history
- tests/test_tickets_velocity.py::TestSprintVelocity::test_reopen_and_reclose_both_counted
- tests/test_tickets_velocity.py::TestSprintVelocity::test_no_tickets_in_sprint_is_empty_not_a_crash
- tests/test_tickets_velocity.py::TestSprintVelocity::test_non_git_root_returns_empty_transitions
- tests/test_tickets_velocity.py::TestModelsAreFrozen::test_sprint_transition_rejects_field_assignment
- tests/test_tickets_velocity.py::TestModelsAreFrozen::test_sprint_velocity_report_rejects_field_assignment
designated_repro_test: null
threat: null
component: null
---
T-0715's user mandate also asked for velocity/burndown derived from
ledger state-transition history (closed-per-sprint counts), explicitly
"no new storage" -- i.e. it must be computed from the same
`frob:tests`/Done-report/state history already in the ledger and git log,
not a new tracked field. This is a real design + implementation gap on
its own: today's `Ticket`/ledger model does not retain a transition-
history log at all (only the CURRENT `state`), so "closed-per-sprint"
needs either (a) mining git log diffs of `tickets.md` for `state: done`
transitions per commit, correlated with each ticket's `sprint` field
(landed by T-0715), or (b) a lightweight append-only transition-log this
ticket would introduce (weighed against the "no new storage" mandate).
Depends on T-0715 (the `sprint` field) being in place first.

Acceptance: GIVEN a sprint with N tickets closed across several commits
WHEN `frob ticket sprint show <label>` (built by the CLI-surface child
ticket) is asked for velocity THEN it reports a closed-count derived
from history, not a hand-maintained counter, and the number matches a
manual `git log` tally of `state: done` transitions for that sprint's
tickets.