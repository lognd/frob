---
id: T-4463
title: 'REL001 ignores v-prefixed milestones: 13 open v0.531.0 tickets invisible to
  the release gate'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: high
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_release*.py
- src/frob/gates/_milestone*.py
- src/frob/tickets/_setters.py
- tests/gates_suite/test_release*.py
- tests/gates_suite/test_milestone*.py
- src/frob/gates/_debt_deprecated.py
- tests/gates_suite/test_debt.py
- tests/test_gates_milestone.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: REL001 lives in _debt_deprecated.py (not _release*.py as scoped -- no such
    file exists) tested by test_debt.py; MILE001/002 tests live at tests/test_gates_milestone.py
    not tests/gates_suite/test_milestone*.py. Widening to the real files that must
    change per acceptance criteria.
  actor: logan
  at: '2026-09-13'
- op: add
  glob: tests/gates_suite/test_debt.py
  reason: REL001 lives in _debt_deprecated.py (not _release*.py as scoped -- no such
    file exists) tested by test_debt.py; MILE001/002 tests live at tests/test_gates_milestone.py
    not tests/gates_suite/test_milestone*.py. Widening to the real files that must
    change per acceptance criteria.
  actor: logan
  at: '2026-09-13'
- op: add
  glob: tests/test_gates_milestone.py
  reason: REL001 lives in _debt_deprecated.py (not _release*.py as scoped -- no such
    file exists) tested by test_debt.py; MILE001/002 tests live at tests/test_gates_milestone.py
    not tests/gates_suite/test_milestone*.py. Widening to the real files that must
    change per acceptance criteria.
  actor: logan
  at: '2026-09-13'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'shared normalizer belongs alongside validate_milestone in _models.py (existing
    dependency direction: gates imports from tickets, not reverse); existing validate_milestone
    tests live in tests/test_tickets.py::TestValidateMilestone, need a normalization
    test there too.'
  actor: logan
  at: '2026-09-13'
- op: add
  glob: tests/test_tickets.py
  reason: 'shared normalizer belongs alongside validate_milestone in _models.py (existing
    dependency direction: gates imports from tickets, not reverse); existing validate_milestone
    tests live in tests/test_tickets.py::TestValidateMilestone, need a normalization
    test there too.'
  actor: logan
  at: '2026-09-13'
evidence:
- tests/test_tickets.py::TestNormalizeMilestone::test_strips_v_prefix
- tests/test_tickets.py::TestNormalizeMilestone::test_bare_form_unchanged
- tests/test_tickets.py::TestValidateMilestone::test_v_prefix_normalized_on_write
- tests/test_tickets.py::TestSetMilestone::test_v_prefix_normalized_on_write
- tests/gates_suite/test_debt.py::TestReleaseOpenMilestoneViolations::test_v_prefixed_ticket_milestone_refuses
- tests/test_gates_milestone.py::TestMile001::test_v_prefixed_and_bare_milestone_treated_equal
- tests/test_gates_milestone.py::TestMile002::test_v_prefixed_and_bare_milestone_treated_equal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-13 at the 0.531.0 cut: `frob check --only release` reported "REL001: release 0.531.0 cannot be cut -- 2 open ticket(s) still carry (effective) milestone 0.531.0: T-4142, T-4236" while thirteen OTHER open tickets carry milestone "v0.531.0" (T-3274, T-3505, T-3512, T-3602, T-3620, T-3659, T-3783, T-3811, T-3918, T-4011, T-4029, T-4448, T-4449). The two counted tickets store the milestone as the bare string "0.531.0"; the thirteen store "v0.531.0". REL001's effective-milestone comparison is a literal string match against the version, so a leading "v" (the form `frob ticket milestone` and the sprint labels use everywhere else in this ledger) silently excludes a ticket from the release gate -- a silent-zero: the gate reports 2 blockers when the ledger has 15. ACCEPTANCE: (1) REL001 normalizes milestone strings (strip a leading v/V, compare PEP 440-normalized) before comparing to the release version, in ONE shared normalizer also used by MILE001/MILE002 and `frob ticket milestone` validation (no duplicated rule); (2) a test with a ticket carrying "v0.531.0" and a release of 0.531.0 asserts REL001 fires; (3) the ledger's existing bare-vs-v mixed forms are reported by a one-time TICK finding or normalized on write. Sprint v0.532.0. Note for the 0.531.0 cut: the thirteen v-prefixed tickets were reviewed by the coordinator; the Windows-drain ones are moot after CI went green and will be re-milestoned by hand.