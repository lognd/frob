---
id: T-0324
title: evidence/COV003 resolution must accept parametrized node ids (file::Class::method[param])
state: done
kind: bug
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/testing/**
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0324 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_parametrized_evidence_with_dot_in_case_id
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_case_with_dot_in_case_id
designated_repro_test: null
threat: null
component: null
---
frob ticket evidence and COV003 reject a specific parametrized case id like ...test_x[015-python-...] (UnknownEvidence), only the bracket-less base resolves. Hit repeatedly this session (T-0222 auto-generated fixture evidence). T-0307 fixed parametrized COUNTING but evidence RESOLUTION of a [param] id is a separate path -- make it resolve a bracketed param id to its collected node. Pairs with T-0298 (file/dir-level evidence).