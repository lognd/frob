---
id: T-1520
title: 'CACHE001 static gate: a cached computation''s observed read-set must be covered
  by its cache-key inputs'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_cache_gate.py
- tests/test_cache_gate.py
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
- tests/_cache_transparency.py
- tests/test_cache_transparency.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_cache_gate.py
  reason: 'CACHE001 static gate: detector core + registry entry + tests, per T-1520''s
    own acceptance floor'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_cache_gate.py
  reason: 'CACHE001 static gate: detector core + registry entry + tests, per T-1520''s
    own acceptance floor'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'CACHE001 static gate: detector core + registry entry + tests, per T-1520''s
    own acceptance floor'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'CACHE001 static gate: detector core + registry entry + tests, per T-1520''s
    own acceptance floor'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/_cache_transparency.py
  reason: 'Landing-repair for the T-1519/T-1520 series: T-1519 is done and its ledger

    state on main already reflects that, so the shared cache-transparency

    harness files (tests/_cache_transparency.py, tests/test_cache_transparency.py)

    lose COV002 coverage the moment they are touched again outside a same-diff

    close grace window. T-1520 is the still-open sibling ticket in this same

    series that both needs these landing-blocker fixes applied and is the only

    open ticket left to carry the frob:ticket edge, so its scope is widened to

    cover these two files for that narrow purpose.

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_cache_transparency.py
  reason: 'Landing-repair for the T-1519/T-1520 series: T-1519 is done and its ledger

    state on main already reflects that, so the shared cache-transparency

    harness files (tests/_cache_transparency.py, tests/test_cache_transparency.py)

    lose COV002 coverage the moment they are touched again outside a same-diff

    close grace window. T-1520 is the still-open sibling ticket in this same

    series that both needs these landing-blocker fixes applied and is the only

    open ticket left to carry the frob:ticket edge, so its scope is widened to

    cover these two files for that narrow purpose.

    '
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_cache_gate.py::TestMemoizedReadCoverage::test_uncovered_read_fires
- tests/test_cache_gate.py::TestT1454RegressionShape::test_env_read_fires
- tests/test_cache_gate.py::TestMemoizedReadCoverage::test_silent_shapes[param-derived-read]
- tests/test_cache_gate.py::TestMemoizedReadCoverage::test_silent_shapes[non-memoized-function]
designated_repro_test: null
threat: null
component: null
---
The recurring cache-bug class is key incompleteness: the computation reads an input the key does not cover, so a change to that input serves a stale result (real incident: T-1454 -- frob ack rewrote frob.lock, no tracked source digest changed, cached DRIFT001 went stale). This is statically checkable with machinery frob already has: the vet/effect scan observes what files/inputs a function reads; a new CACHE001 detector requires every memoize_per_run/persistent-cache-backed computation to declare its key inputs (content hashes, config fields, lock files) and errors when the observed read-set is not covered by the declared keys -- prove-or-justify, with frob:waive+ticket for genuinely dynamic reads. This makes cache correctness a GATE, not a hope, per the static-quality vision (cannot write bad code silently) and the perf-findings-become-lint-rules rule. Pairs with the observational-transparency invariant ticket filed alongside this one.