---
id: T-0526
title: 'frob:debt/frob:todo coherence: paired todo, same-ticket check, symmetric resolution'
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: T-0412
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: T-0526 debt/todo coherence needs regression tests in the existing dsl.py
    test file
  actor: logan
  at: '2026-07-21'
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1861
evidence:
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_unpaired_debt_registers_implicit_todo
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_explicit_paired_todo_same_ticket_no_implicit_duplicate
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_mismatched_explicit_todo_is_debt001_shaped_malformed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
<!-- narrative-moved:src/frob/graph/dsl.py:1628:T-0526 -->
T-0526: frob:debt/frob:todo coherence.

A `frob:debt` suppresses a GATE FINDING (the symptom); a `frob:todo`
tracks DEFERRED WORK (the payoff). Per T-0412's own follow-up
requirement, a debt without visible payoff-work must not be a silent
suppression: (1) a `frob:debt` at a site with no co-located explicit
`frob:todo` implicitly REGISTERS one -- same `src`, target is the debt's
own `ticket=` attribute -- so the debt's payoff work appears in every
ordinary todo-edge consumer (the "002" open-ticket check, `frob todo`-
style listings) for free, with no separate debt/todo wiring anywhere
else. (2) both directives already require an open ticket today (the
debt check reuses the same open-ticket check the todo gate applies, per
T-0412's Done report), so an implicit registration is just as enforced
as an explicit one. (3) a `frob:debt` and an EXPLICIT co-located
`frob:todo` naming DIFFERENT tickets is a coherence error: reusing
DEBT001's own `"frob:debt" in md.reason` substring filter
(`frob.gates._debt001_violations`) by shaping the `MalformedDirective`
reason to contain that literal substring, so the mismatch surfaces as a
DEBT001 violation with no new gate rule id and no `frob.gates` change at
all -- this coherence rule lives entirely in the DSL parse step, exactly
like DEBT001/TEST010's existing "shape the malformed reason, let an
established gate's substring filter pick it up" pattern.

Requirement (4) from T-0412's body -- surfacing BOTH the debt and its
todo at ticket-close time so neither resolves silently -- is NOT
implemented here: it is ticket-lifecycle behavior belonging to
`frob.tickets`/`frob.gates`, outside this module's declared scope
(T-0526 scopes only `src/frob/graph/dsl.py`). Filed as its own follow-up
rather than folded in silently; see T-0526's Done report.