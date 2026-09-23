---
id: T-4608
title: 'macOS CI: test_overhead_under_five_percent crashes its xdist worker, aborting
  the whole suite via rerunfailures IPC'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.542.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/perf/test_hotgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.542.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Latest completed dev CI run (35223985836, headSha bcd55a738), macos-latest job (105210788764): the suite aborted with SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR), collected=14384 (partial), cause=AssertionError: ('tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent', <WorkerController gw2>).

Traceback shows the crash surfaces inside pytest-rerunfailures' own IPC: xdist's worker_workerfinished -> assert not crashitem fires because gw2's worker process for this exact test node is gone; the INTERNALERROR itself originates in pytest_rerunfailures.py's get_test_failures -> _get -> _sock_recv -> "OSError: [Errno 9] Bad file descriptor" (the rerun-history socket to the coordinator is already closed when this worker tries to query it).

This matches the exact failure class ci.yml's own T-3776/T-3777 comment already documents ("pytest-rerunfailures 16.6 INTERNALERRORs under xdist on py3.14 (macos), turning a rare flake into a whole-suite abort; flakes are handled by fixing the specific flaky tests instead (T-3775)") -- that policy names this exact test as the next one needing its own ticket, per T-3775's own per-test-ticket naming pattern.

Two things need resolving, in order: (1) why does test_overhead_under_five_percent's own xdist WORKER PROCESS die on macos/py3.14 in the first place (a real crash upstream of the rerunfailures IPC failure -- possibly a py3.14-specific interaction with StackSampler's background-thread sys._current_frames() sampling, possibly an OOM/resource kill on the runner, unconfirmed); (2) once that is understood, whether test_overhead_under_five_percent itself needs adjusting (e.g. skip/xfail on py3.14+darwin, reduce iteration count, or a documented tolerance/backend change) or whether this is purely a pytest-rerunfailures-under-xdist infra bug this repo cannot fix from its own tree.

Not reproducible in this session: no macOS execution environment available (Linux/WSL only; ~/bin/winrun mirrors Windows, not macOS). Needs either a macOS runner/CI re-run with -rA --tb=short (already the ubuntu/macos steps' verbosity) or someone with local macOS access to reproduce test_overhead_under_five_percent under -n auto --dist=loadgroup on py3.14 specifically.

## Failure log
- 2026-09-19 attempt 1: no macOS execution environment available in this session to reproduce/diagnose the py3.14+darwin xdist-worker crash in pytest-rerunfailures' IPC; forcing a speculative skipif/timeout change without reproducing the crash risks masking a real StackSampler bug -- needs a macOS-capable agent or a CI re-run with -rA --tb=short for a full traceback
