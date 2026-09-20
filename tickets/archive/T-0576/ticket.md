---
id: T-0576
title: 'frob:deprecated directive: API sunset dates gated like debt'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- src/frob/graph/_models.py
- src/frob/gates/__init__.py
- src/frob/gates/_models.py
- docs/modules/gates.md
- docs/guides/extending/comment-dsl-directives.md
- tests/test_gates.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/graph/_models.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/gates/_models.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/guides/extending/comment-dsl-directives.md
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_gates.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'T-0576: frob:deprecated directive parse (dsl.py/_models.py), DEPR gate
    family + release wiring (gates/__init__.py, _models.py DeprecatedEntry), docs,
    tests'
  actor: logan
  at: '2026-07-22'
body_changes:
- mode: append
  reason: 'T-4709: preserve DEPR003/DEPR002 rationale trimmed from _debt_deprecated.py'
  actor: logan
  at: '2026-09-19'
  old_length: 284
  new_length: 979
evidence:
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr001_malformed_directive_is_reported
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr001_malformed_sunset_is_reported
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr002_closed_ticket_is_reported
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr003_in_window_warns
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_depr004_past_sunset_errors
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_lists_every_deprecated_entry
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_release_gate_fails_while_deprecated_is_past_sunset
- tests/gates_suite/test_debt.py::TestDeprecatedGate::test_release_gate_silent_while_deprecated_in_window
- tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_well_formed_directive_parses_to_deprecated_edge
- tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_missing_sunset_is_malformed
- tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_missing_ticket_is_malformed
- tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_non_date_sunset_is_malformed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:debt generalized to API surface: frob:deprecated <since> sunset=<date> ticket=T-#### on a public symbol; a gate warns while in window, errors past sunset or when the ticket closes without removal; release refuses to stamp with expired deprecations. Scope: graph dsl, gates, docs.


T-4709 follow-up (condensed from the deprecated-symbol-gate comment
block in src/frob/gates/_debt_deprecated.py, trimmed for DOCARCH002's
12-line cap): DEPR003 exists because `frob:debt` has no equivalent
"still valid" signal; a deprecated PUBLIC symbol needs one, per this
ticket's own body. DEPR002 suppresses DEPR003/DEPR004 when the ticket
itself is not open, since a mistracked deprecation is the more
actionable finding. `release_gate`'s check is
`_release_expired_deprecated_violations`; the point of only blocking
on EXPIRED deprecations is that an unenforced sunset never quietly
survives past its own date, while a still-live one within its warning
window does not block a release.