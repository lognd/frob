---
id: T-0584
title: 'PRE001 catch-22 on slow mounts: sweep needs a timeout/partial-state or async
  design (T-0355 item 2)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'gate:AFFECT/COV forced a doc update in docs/modules/gates.md for the PreworkSweep/sweep_ticket/prework_gate
    changes this ticket makes; widening scope to include the doc file the code''s
    own frob:doc anchor already points at.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestScopePrework::test_pre001_passes_with_partial_sweep_matching_digest
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_partial_on_budget_exceeded
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_resumes_pending_patterns
- tests/test_gates.py::TestScopePrework::test_prework_sweep_default_partial_is_false_and_treated_as_final
designated_repro_test: null
threat: null
component: null
---
found while working T-0355 (deliberately split out, item 2 of that ticket's original 3-item report): editing a ticket's scope after start demands a re-sweep before PRE001 is satisfiable, and frob ticket sweep's dup+xref pass is a synchronous full-scope scan -- on a slow mount (WSL /mnt/c, network share) that scan itself can be slow enough that the ticket can never get back into a checkable state within a reasonable session. T-0474 already backgrounds the sweep at frob ticket start time, but frob ticket sweep (the always-available resweep path used after a scope edit) is still fully synchronous by design (see its docstring: 'the always-available, always-synchronous way to record it'), and PRE001 itself only ever compares against a fully-completed digest -- there is no partial-sweep-ok state. This needs an actual design decision before implementation (a timeout + partial-sweep-ok ticket state that prework_gate treats as provisionally clean, vs. making frob ticket sweep itself background-and-poll like start), not a mechanical port of an existing fix, so it was NOT implemented as part of T-0355 (items 1 and 3 of that ticket were: clean SIGINT message in __main__.py, and confirming scope_digest is already content-only/checkout-portable).