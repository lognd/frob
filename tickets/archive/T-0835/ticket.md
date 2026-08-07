---
id: T-0835
title: 'tickets: start does not refuse done tickets or live leases in other worktrees
  (double-dispatch hit live)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_leases.py
- src/frob/__main__.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: 'T-0835 requires an explicit `--steal` CLI flag on `frob ticket start` to

    override a live cross-worktree lease refusal. Wiring a new CLI flag

    necessarily touches the argparse definition (src/frob/__main__.py) and the

    AppConfig field/passthrough allowlist (src/frob/app/config.py) that every

    other ticket-mutating flag already goes through (e.g. ticket_foreground).

    Minimal, mechanical addition only -- one bool field, one add_argument call,

    one passthrough-allowlist entry -- no unrelated changes to either file.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-0835 requires an explicit `--steal` CLI flag on `frob ticket start` to

    override a live cross-worktree lease refusal. Wiring a new CLI flag

    necessarily touches the argparse definition (src/frob/__main__.py) and the

    AppConfig field/passthrough allowlist (src/frob/app/config.py) that every

    other ticket-mutating flag already goes through (e.g. ticket_foreground).

    Minimal, mechanical addition only -- one bool field, one add_argument call,

    one passthrough-allowlist entry -- no unrelated changes to either file.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
- tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_dropped_ticket
- tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_refuses_live_lease_in_another_worktree
- tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
- tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_same_worktree_restart_stays_idempotent
- tests/test_ticket_leases.py::TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease
- tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end
designated_repro_test: null
threat: null
component: null
---
Hit live 2026-07-23: T-0806 was dispatched twice (first agent presumed
dead, redispatched); the first agent's work landed at 04:45 while the
second agent was still diagnosing in its own worktree -- 5.5h of
duplicate work. The second agent's `frob ticket start T-0806` succeeded
(queued -> planned) even though another worktree held a live lease, and
the ticket later reached done while the duplicate ran on.

Fix: `frob ticket start` must refuse (a) tickets in done/dropped state
(actionable message naming the landing commit if derivable), and (b)
tickets holding a live lease pinned to a DIFFERENT worktree (name the
worktree and lease age; require an explicit --steal to override, which
must invalidate the old lease so the loser cannot silently land). Both
refusals need tests.