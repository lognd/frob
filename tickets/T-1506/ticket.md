---
id: T-1506
title: 'docenum: widen _extract_members to resolve argparse choices=[...] lists'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docenum.py
- tests/test_docenum_gate.py
- tickets/T-1506/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_docenum_gate.py
  reason: 'T-1506: unit tests for the new argparse choices=[...] extraction shape'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1506/**
  reason: 'T-1506: own ticket dir needed in scope (Done report/ledger files)'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_choices_members_extracted
- tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_choices_stale_claim_fires
- tests/test_docenum_gate.py::TestDocenum001Gate::test_argparse_multiple_choices_calls_is_ambiguous_punt
designated_repro_test: null
threat: null
component: null
---
frob.gates._docenum's `_extract_members` cannot resolve argparse
`choices=[...]` lists (cycle.md/xref.md --lang, parse.md tool table) --
a `parser.add_argument(..., choices=[...])` call site has no bare
module/class-level assignment target `_find_node_for_qualname` can walk
to at all. Widen `_extract_members` to this shape so doc-enum coverage
extends to CLI choices lists the same way it already covers
Literal/frozenset assignments.

Follow-up filed as the TICK0/TODO002 remediation for the dangling
`frob:todo T-draft-323551f5` directive at
src/frob/gates/_docenum.py::_extract_members (drain-to-zero warning
burn-down, this ticket) -- that draft id was never actually filed as a
real ticket.