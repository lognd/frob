---
id: T-2965
title: frob ticket set-parent needs a --clear path to detach a mis-parented ticket
  to root
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: 0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/_config_external.py
- docs/modules/tickets.md
- tests/test_tickets_parent.py
- src/frob/_cli_parsers/_ticket/_metadata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: --clear flag
  actor: logan
  at: '2026-09-17'
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-16'
- field: milestone
  old_value: v0.533.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-16'
body_changes:
- mode: set
  reason: 'DOC006: planned or rejected CLI forms written as prose so unrelated lands
    are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 1801
  new_length: 1787
evidence:
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_detaches_to_root
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_records_a_triage_entry
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_on_already_root_ticket_refuses
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_requires_a_reason
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_skips_structural_validation
- tests/test_tickets_parent.py::TestSetParentClear::test_clear_on_archived_ticket_routes_to_archive_path
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_clear_with_no_parent_id
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_parent_id_with_no_clear
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_both_together_argparse_alone_does_not_refuse
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_refuses_both_parent_id_and_clear
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_refuses_neither_parent_id_nor_clear
- tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_clear_detaches_via_the_cli_config_shape
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured directly while working T-2959: the planned ticket set form (T-2770, src/frob/tickets/_setters.py::set_parent) has no
route to CLEAR a ticket's parent edge back to `null` -- `parent-id` is
a required positional argument and `_validate_parent_edge` refuses any
value that does not resolve to an existing ticket in the queue
(`TicketError.ParentNotFound`). The function's own docstring confirms
this is by design for its ORIGINAL motivating case (T-2770's own
"successor work filed with `parent: null`... re-parenting the
successor ONTO the epic is the fix" -- one-directional, attach only).

The inverse case has no tooling: a ticket mis-parented under the WRONG
epic, whose correct parent is genuinely `null` (it should be a
top-level/root ticket), cannot be fixed without either (a) hand-editing
`ticket.md` frontmatter directly -- forbidden by this repo's own
playbook and by `_TICKET_FROZEN_FIELDS`-style discipline for every
other ledger-owned field, or (b) inventing a placeholder parent ticket
just to have something valid to point at (T-2959's own workaround: a
brand-new top-level epic, T-2964, was filed specifically so T-2384
had somewhere real to move to -- legitimate in that case because T-2384
genuinely needed a portability-epic home, but NOT a general solution
for a ticket that should have no parent at all, e.g. a genuinely
free-standing bug).

Add a `--clear` (or `--none`/`--detach`) flag to `frob ticket
set-parent` that writes `parent: null` directly, going through the
same reason-required, land-in-progress-refusing, single-writer path
`set_parent` already uses -- not a new bypass. `_validate_parent_edge`
needs no change (a null target skips validation entirely, same as
`Ticket.parent` already defaults to `None` for a ticket filed with no
`--parent`).