---
id: T-1330
title: Wire v2 git-history mining into frob ticket flow/sprint velocity
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_setters.py
- tests/test_tickets_velocity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v2_mode_mines_via_v2_state_transitions
- tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history
designated_repro_test: null
threat: null
component: null
---
T-1257 built the v2-mode git-history mining primitive
(`frob.tickets._store.v2_state_transitions`, design section 4.4) but did
NOT wire it into the user-facing `frob ticket flow` command --
`_setters.py`'s `_ledger_commit_history`/`_blob_at`/`_mine_done_transitions`
family is hardcoded to `git log ... -- tickets.md` (the v1 monofile path)
and is out of T-1257's declared scope
(src/frob/tickets/_doable.py, src/frob/tickets/_store.py,
src/frob/app/ticket_runner/**, tests/test_tickets.py).

Follow-up: branch `frob ticket flow` (and `sprint velocity`, same family)
on `_store_mode(root)` -- v2 mode should mine per-ticket history via
`v2_state_transitions` for every ticket instead of walking one shared
`tickets.md` blob. Needs its own SprintTransition-shaped adapter and a
parity test against the v1 path for an equivalent ticket set (mirrors
T-1257's acceptance criterion 3, not yet closed by that ticket).