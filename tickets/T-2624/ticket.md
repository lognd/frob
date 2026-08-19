---
id: T-2624
title: CLI wiring for runs_last_parallel_safe
state: in-progress
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: true
runs_last_parallel_safe_reason: test declaration for CLI smoke check
scope:
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_new.py
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/_config_external.py
- tests/test_tickets_organization.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: T-2579 left the field model-only; the CLI verb (frob ticket runs-last-parallel-safe)
    and frob ticket new flags require argparse registration (in _cli_parsers/_ticket/_metadata.py,
    _new.py, __init__.py) and TicketSpec construction/validation wiring (tickets/_new_renumber.py,
    app/ticket_runner/_new.py) that the ticket's original scope list omitted -- same
    shape as scope_breadth_ack's own wiring, spread across these exact files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: T-2579 left the field model-only; the CLI verb (frob ticket runs-last-parallel-safe)
    and frob ticket new flags require argparse registration (in _cli_parsers/_ticket/_metadata.py,
    _new.py, __init__.py) and TicketSpec construction/validation wiring (tickets/_new_renumber.py,
    app/ticket_runner/_new.py) that the ticket's original scope list omitted -- same
    shape as scope_breadth_ack's own wiring, spread across these exact files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: T-2579 left the field model-only; the CLI verb (frob ticket runs-last-parallel-safe)
    and frob ticket new flags require argparse registration (in _cli_parsers/_ticket/_metadata.py,
    _new.py, __init__.py) and TicketSpec construction/validation wiring (tickets/_new_renumber.py,
    app/ticket_runner/_new.py) that the ticket's original scope list omitted -- same
    shape as scope_breadth_ack's own wiring, spread across these exact files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: T-2579 left the field model-only; the CLI verb (frob ticket runs-last-parallel-safe)
    and frob ticket new flags require argparse registration (in _cli_parsers/_ticket/_metadata.py,
    _new.py, __init__.py) and TicketSpec construction/validation wiring (tickets/_new_renumber.py,
    app/ticket_runner/_new.py) that the ticket's original scope list omitted -- same
    shape as scope_breadth_ack's own wiring, spread across these exact files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: T-2579 left the field model-only; the CLI verb (frob ticket runs-last-parallel-safe)
    and frob ticket new flags require argparse registration (in _cli_parsers/_ticket/_metadata.py,
    _new.py, __init__.py) and TicketSpec construction/validation wiring (tickets/_new_renumber.py,
    app/ticket_runner/_new.py) that the ticket's original scope list omitted -- same
    shape as scope_breadth_ack's own wiring, spread across these exact files
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: set_runs_last_parallel_safe (like set_scope_breadth_ack) must be re-exported
    from frob.tickets's package __init__ for _mutate.py/_new_renumber.py to import
    it
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/ticket_runner/_ledger_mirror.py
  reason: the runs-last-parallel-safe CLI verb needs a LedgerWriteStrategy entry (GENERIC_COMMIT_MIRRORED,
    same as scope-ack/runs-last) or the fleet mirror silently mishandles it
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's field-name tuples (_STRING_FIELDS/_BOOL_FIELDS)
    must list ticket_runs_last_parallel_safe/_reason or the new frob ticket new flags
    parse but never populate cfg
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_tickets_organization.py
  reason: T-2624's own frob:tests evidence lives here (TestSetRunsLastParallelSafe,
    TestRunsLastParallelSafeCli, TestMile004ParallelSafeCliEndToEnd)
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'AFFECT001 fires on _ledger_mirror.py::LEDGER_VERB_STRATEGY: the new runs-last-parallel-safe
    verb entry needs its affects()-closure doc (docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603)
    touched in the same diff'
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2579 (M4b) added Ticket.runs_last_parallel_safe / _reason (bool+reason
pair, same shape scope_breadth_ack/scope_breadth_ack_reason already
uses) and the MILE004 gate that reads it, but wiring a way to actually
SET the field was out of T-2579's declared scope (src/frob/gates/
_milestone.py, src/frob/gates/__init__.py, src/frob/tickets/_models.py
only -- no _setters.py, _new_renumber.py, _mutate.py/_lifecycle.py).

Needed: a retroactive setter set_runs_last_parallel_safe(root,
ticket_id, reason) in src/frob/tickets/_setters.py (same
_set_ticket_field-adjacent pattern set_scope_breadth_ack uses) plus a
frob ticket runs-last-parallel-safe <id> --reason TEXT CLI verb wired
the same way frob ticket scope-ack is; and frob ticket new
--runs-last-parallel-safe --runs-last-parallel-safe-reason TEXT for
filing-time declaration (TicketSpec already carries both fields).

Until this lands, runs_last_parallel_safe can only be set by directly
constructing a Ticket/editing the ledger file, which is how T-2579's
own tests exercise MILE004 -- fine for gate-logic verification, not fine
for a real operator declaring two runs-last tickets parallel-safe.
