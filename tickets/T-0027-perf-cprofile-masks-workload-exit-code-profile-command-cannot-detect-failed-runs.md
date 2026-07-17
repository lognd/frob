---
id: T-0027
title: 'perf: cProfile masks workload exit code; profile_command cannot detect failed
  runs'
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
evidence: []
attachments: []
---
found while working T-0021: python -m cProfile exits 0 even when the profiled program exits nonzero (verified: pytest usage error exit 4 -> wrapped exit 0). profile_command therefore records a successful artifact for a workload that never ran. Consider a shim entry that captures SystemExit and records the real returncode in the meta sidecar.