---
id: T-2931
title: Generalize WIRE001's dynamic-dispatch exemption to recognize atexit.register
  callbacks
state: in-progress
kind: feature
origin: human
created: '2026-08-25'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/_wire.py
- tests/unit/test_wire001_atexit_register.py
- tickets/T-draft-56527a0d/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_wire001_atexit_register.py
  reason: new must-fire/must-stay-quiet fixture file, plus the filed follow-up ticket's
    own ledger file
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-draft-56527a0d/ticket.md
  reason: new must-fire/must-stay-quiet fixture file, plus the filed follow-up ticket's
    own ledger file
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`_unlanded.py::_remove_scratch_file`'s only caller is `atexit.register(_remove_scratch_file, path)` inside `_scratch_file_for_suffix` (T-2645) -- a dynamic registration WIRE001's call-graph resolver structurally cannot see, the same class of gap this repo already carved a named exemption for (`frob.gates._waive._WIRE001_RESCUE_EXEMPT_RULE`, covering autouse pytest fixtures and pydantic validators).

Generalize that exemption (or add a sibling one) to recognize `atexit.register(<callback>, ...)` as a valid dynamic-dispatch pattern, so a genuinely-only-atexit-called private function does not need a per-site `frob:waive WIRE001 follow_up=...` that requires perpetually pointing at SOME open ticket forever.

Scope: src/frob/gates/_waive.py (the exemption predicate), src/frob/gates/_wire.py (the WIRE001 gate itself, if the exemption needs to be consulted there instead).
