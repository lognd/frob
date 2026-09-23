---
id: T-4657
title: 'Typed ledger store API: one module every frob module reads and writes tickets
  through'
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4652
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store_api.py
- tests/unit/test_ledger_store_api.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
- tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error
- tests/unit/test_ledger_store_api.py::test_docs_name_store_api_as_the_entry_point
- tests/unit/test_ledger_store_api.py::test_put_then_get_round_trips
- tests/unit/test_ledger_store_api.py::test_archived_put_then_get_round_trips
designated_repro_test: null
acceptance:
- text: Given src/frob/tickets/_store_api.py exists, when another frob module needs
    to read or write a ticket, then it imports _store_api and never opens tickets/<id>/ticket.md
    itself.
  evidence:
  - tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
- text: 'POSITIVE CONTROL: tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
    asserts that no src/frob module other than _store_api.py performs a read/write
    against a tickets/**/ticket.md path. This test FAILS on dev today (multiple such
    sites exist) and passes after this leaf.'
  evidence:
  - tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
- text: Given a fallible store operation, when it fails, then it returns a typani
    Result error value rather than raising; tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error
    proves it.
  evidence:
  - tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error
  - tests/unit/test_ledger_store_api.py::test_put_then_get_round_trips
  - tests/unit/test_ledger_store_api.py::test_archived_put_then_get_round_trips
- text: docs/modules/tickets-data-storage.md names _store_api as the single entry
    point and is updated in this same change.
  evidence:
  - tests/unit/test_ledger_store_api.py::test_docs_name_store_api_as_the_entry_point
evidence_changes:
- old_node: tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error
  new_node: ''
  reason: was bound to the wrong acceptance index (positive control [2]); moving to
    [3] (Result-error contract) which is what it actually proves
  actor: logan
  at: '2026-09-19'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel decoupling leaf (LEDGER story). ~3 points.

Today ticket data is reached a dozen different ways across src/frob/tickets/*.py (_store.py is 2536 lines and is only one of the readers) and src/frob/app/ticket_runner/*.py. That is why the ledger, the leases and the land cannot be separated: there is no seam.

Build ONE typed store API module, src/frob/tickets/_store_api.py: pydantic models in, pydantic models out, every fallible operation returning a typani Result[T, E]. Every other module goes through it; nothing else opens tickets/<id>/ticket.md.

Do NOT change the on-disk ticket.md format or the CLI. This leaf introduces the seam and migrates the readers the positive control names; a follow-up may migrate the rest.

Log every read and write at DEBUG with ticket id and operation, every refusal at WARNING.