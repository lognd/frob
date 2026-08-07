---
id: T-1049
title: 'refactor: decompose oversized _build_jobs gate-job registry (ARCH001)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
designated_repro_test: null
threat: null
component: null
---
frob check --ticket T-0602 flags ARCH001 on src/frob/gates/__init__.py::_build_jobs
(201 lines, threshold 60). This is PRE-EXISTING: main already has this function
at 196 lines (verified via git show main:src/frob/gates/__init__.py) -- it is
one large dict-literal gate-job registry (thread_jobs + process_jobs mapping),
not something T-0602 introduced. T-0602 only added ~8 net lines (a `use_cache`
param and one call to a newly extracted `_substitute_cacheable_jobs` helper),
which was enough to lose ARCH001's grandfather exemption for a function this
ticket's diff merely touches rather than substantially grows.

Decompose _build_jobs's thread_jobs/process_jobs dict-literal assembly into
smaller per-concern builder functions (e.g. one for the always-run set, one
for the ticket-scoped set, one for the process-pool set) so the function
itself drops under the ARCH001 threshold. Out of T-0602's scope
(src/frob/gates/**, src/frob/serve/**, tests/test_gate_cache.py,
docs/modules/{serve,gates}.md) -- this refactor would touch the entire
existing gate-job assembly, not the T-0602 feature itself.