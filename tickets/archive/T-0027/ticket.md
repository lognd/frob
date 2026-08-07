---
id: T-0027
title: 'perf: cProfile masks workload exit code; profile_command cannot detect failed
  runs'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/perf_runner.py
- src/frob/perf/**
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_profile_records_workload_exit_code
- tests/test_perf.py::test_profile_clean_workload_exit_zero
designated_repro_test: null
threat: null
component: null
---
found while working T-0021: python -m cProfile exits 0 even when the profiled program exits nonzero (verified: pytest usage error exit 4 -> wrapped exit 0). profile_command therefore records a successful artifact for a workload that never ran. Consider a shim entry that captures SystemExit and records the real returncode in the meta sidecar.