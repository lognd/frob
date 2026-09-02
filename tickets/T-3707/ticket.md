---
id: T-3707
title: 'win32 round 23: explicit executor shutdown for check pipeline post-submit
  120s gap'
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- .github/workflows/ci.yml
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
Follow-up to T-3692. CI run 33680767948 FROB_CHECK_TIMING breadcrumbs: every pipeline mark fires at ~1.0s, then a ~120s gap before atexit fires. Investigated frob.gates._open_process_pool: already properly torn down (shutdown(wait=True) in finally; teardown-exit marks land at ~1s) -- NOT the blocker. Real suspect found while narrowing, out of this scope, filed separately: src/frob/lang and src/frob/vet abandon ThreadPoolExecutor(max_workers=1) workers via shutdown(wait=False) on timeout; concurrent.futures.thread joins ALL such threads at interpreter atexit regardless of abandonment. In-scope work: (1) harden _open_process_pool/run_gates shutdown to context-manager + cancel_futures=True with a regression test proving no live pool threads/children survive run_check; (2) Part B watchdog total-budget + ci.yml budget var fix.