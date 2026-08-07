---
id: T-1489
title: TEST011 escalates from advisory WARN to a blocking freshness contract for stale
  coverage
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: TEST017's rule id needs registering in _KNOWN_GATE_RULES (_waive.py) for
    waiver-scan/gate discovery to recognize it, alongside the gate function itself
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: TEST017's frob:enforces CHK-GATE-TEST017 code anchor needs a matching registry
    record in check-coverage.yaml, same as every other TEST0xx rule's entry in this
    file
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction
- tests/test_gates.py::TestTestGate::test_test011_fires_on_stale_mtime
- tests/test_gates.py::TestTestGate::test_test011_silent_when_fresh_and_fully_joined
designated_repro_test: null
threat: null
component: null
---
T-1205 acceptance[1]'s second half (the first half -- TEST005 stale-and-disclosed marking -- landed in T-1205's own session). TEST011 currently WARNs on stale_by_mtime/deflated join fraction; this ticket makes staleness a genuine blocking contract (ERROR-severity, or a dedicated new rule) once the disclosure half has had time to be adopted without breaking every existing checkout at once. Needs its own investigation into rollout sequencing (a same-session flip to ERROR would gate the whole repo on every slightly-stale coverage.xml, which is common in normal dev flow) -- do not just flip severity without that review.