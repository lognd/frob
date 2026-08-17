---
id: T-2118
title: DirtyMain refusal should name the OWNING ticket when dirt belongs to another
  open ticket, not just no-ticket
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
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: COV002/BUG002 evidence for T-2118 lives in this test file
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_land.py::TestDirtOwnerTickets::test_dirty_main_refusal_names_the_owning_ticket
- tests/test_ticket_land.py::TestDirtOwnerTickets::test_path_owned_by_another_open_ticket_names_it
- tests/test_ticket_land.py::TestDirtOwnerTickets::test_path_owned_by_landing_ticket_itself_is_excluded
- tests/test_ticket_land.py::TestDirtOwnerTickets::test_path_owned_by_no_open_ticket_is_excluded
designated_repro_test: tests/test_ticket_land.py::TestDirtOwnerTickets::test_dirty_main_refusal_names_the_owning_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2071's acceptance criterion 2 wants a DirtyMain refusal that names the offending path AND identifies it as foreign to the LANDING ticket. _dirt_owned_by_no_open_ticket (src/frob/tickets/_land.py) already distinguishes 'owned by no open ticket at all' (T-1699) from the generic case, but the real incident shape (T-2071's own measured evidence) is dirt that DOES belong to some OTHER open ticket's declared scope, just not the landing ticket's. That shape currently falls through to the generic 'has uncommitted changes in: ...' message with no mention of which ticket owns it. _log_dirty_main_refusal should also compute, per dirty path, whether it falls in some non-terminal ticket's scope OTHER than the landing ticket, and if so name that ticket id explicitly (not just 'no open ticket'/generic). Could not be done under T-2071 itself: src/frob/tickets/_land.py was held by T-2105's LIVE cross-worktree lease for the duration of T-2071's own work.