---
id: T-0276
title: 'fix(gates): package-level violations (TEST003) can never be waived'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test003_waiver_in_a_file_under_the_package_matches
designated_repro_test: null
threat: null
component: null
---
Coordinator-reported bug (Bug C, feldspar FROBLEMS.md 2026-07-18):
hypothesized as `check_type = "python"` gating Rust `.rs` directives
out of the comment-DSL parse graph entirely (both `frob:tests` bindings
and a `frob:waive TEST003` mitigation attempt reported `0 waived`).