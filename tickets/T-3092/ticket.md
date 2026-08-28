---
id: T-3092
title: Warn when a FEATURE/BUG ticket closes with an empty code diff
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_empty_diff_close.py
- src/frob/gates/_waive.py
- src/frob/gates/_tickets_gate.py
- tests/test_gates_empty_diff_close.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: 'narrow the package glob to the exact files this ticket touches: new gate
    module wired into the existing tickets_gate() dispatch (avoids gates/__init__.py
    and docs/modules/gates.md, both leased by in-progress T-2988), rule-id registration,
    tests'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_empty_diff_close.py
  reason: 'narrow the package glob to the exact files this ticket touches: new gate
    module wired into the existing tickets_gate() dispatch (avoids gates/__init__.py
    and docs/modules/gates.md, both leased by in-progress T-2988), rule-id registration,
    tests'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'narrow the package glob to the exact files this ticket touches: new gate
    module wired into the existing tickets_gate() dispatch (avoids gates/__init__.py
    and docs/modules/gates.md, both leased by in-progress T-2988), rule-id registration,
    tests'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'narrow the package glob to the exact files this ticket touches: new gate
    module wired into the existing tickets_gate() dispatch (avoids gates/__init__.py
    and docs/modules/gates.md, both leased by in-progress T-2988), rule-id registration,
    tests'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_gates_empty_diff_close.py
  reason: 'narrow the package glob to the exact files this ticket touches: new gate
    module wired into the existing tickets_gate() dispatch (avoids gates/__init__.py
    and docs/modules/gates.md, both leased by in-progress T-2988), rule-id registration,
    tests'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: T-3092's TICK014 needs a frob:doc anchor; docs/modules/gates.md is leased
    by in-progress T-2988, so the anchor goes in tickets-data-storage.md instead,
    alongside MILE003/MILE004's own anchors for the same tickets_gate() dispatch family
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
acceptance:
- text: Given a BUG-kind ticket with no scope exemption closes with a diff touching
    only tickets/, when the check runs, then it WARNs
  evidence: []
- text: Given a docs-kind, epic-tier, or no_scope_declared ticket closes with an empty
    code diff, when the check runs, then it stays quiet (fixture per exemption)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3087 follow-up (deferred, optional per its own brief). A done-report that says work was NOT implemented, on a land whose diff touches nothing outside tickets/, is mechanically detectable: a FEATURE- or BUG-kind ticket closing with an empty code diff should be at minimum a WARN. Needs a frob.gates-level diff scan at close/land time (frob.tickets deliberately stays free of frob.gates, per _done_transition_guard's own docstring on why covers_scope/mutation_evidence/etc are injected booleans, never computed in-package). Exemptions required: docs-kind, epic-tier, no_scope_declared tickets legitimately close without code -- each needs its own must-stay-quiet fixture. T-3064 (closed done with a done-report literally saying "T-3064 is BLOCKED, not implemented" and a land touching only tickets/) is the motivating measured incident.