---
id: T-4122
title: SCOPE002 closure cascades unboundedly through design/frob.strata via any conftest.py
  hook's pre-existing frob:tests binding
state: dropped
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4103 (fix pytest_sessionfinish's mid-line SUITE-RESULT write). frob.toml promotes SCOPE002 to error. Declaring scope=['tests/conftest.py'] to fix pytest_sessionfinish pulls in the doc/test-edge closure for EVERY OTHER symbol in conftest.py too (not just the one touched), including pytest_configure's pre-existing frob:tests binding to tests/test_mutate_journal.py. That test covers src/frob/mutate, whose frob:doc anchor lives in docs/modules/mutate.md, which frob:describes design/frob.strata::frob.mutate -- and design/frob.strata is the whole-project design root: adding it to scope immediately demanded 227+ further doc-edge closures (roadmap.md, claude-hooks.md, etc.), unbounded in practice.

Reproduced directly:
  frob ticket scope T-4103 --add design/frob.strata --reason "..."
  frob check --ticket T-4103 --only scope
shows the 227-warning cascade landing on design/frob.strata alone.

The closure-triple walk in _scope002_edge_gap_violations/_scope002_helper_gap_violations has no cap or cycle-break once it reaches a monolithic shared node like design/frob.strata -- needs either (a) a closure depth/fanout cap with a documented escape hatch, or (b) treating a design-root/monolithic-doc node as a closure terminator the way _rule_id_scan.py's own T-1010/T-1937 COV001 waivers already treat docs/modules/gates.md as disproportionate to pull into a narrow ticket's scope.

Worked around in T-4103 via frob ticket scope-ack rather than chasing the cascade.

## Drop reason
- 2026-09-06: duplicate of already-tracked SCOPE002 closure-explosion family (T-3299/T-3902/T-3957/T-4098); no new ticket needed
