---
id: T-3670
title: 'win32 round 16: 4-variant diag matrix -- discriminate uv vs ProcessPoolExecutor
  sender'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- src/frob/process/_guard.py
- src/frob/gates/__init__.py
- src/frob/check/**
- tests/test_ci_workflow_matrix.py
- tests/unit/test_process_guard.py
- docs/modules/process.md
- tests/unit/test_gates_pool_preload.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_gates_pool_preload.py
  reason: new unit test file for the FROB_DISABLE_POOL_PRELOAD serial-fallback path,
    cited in the ticket body's plan
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33533123354's round-15 matrix verdict is decisive: variant (b)
(FROB_DISABLE_EXEC=1, zero guarded tool children) STILL received the
SIGINT. The T-3648-SIGNAL line printed BEFORE the four "refusing to
spawn" warnings, elapsed 1.35s, exit 130 -- so ZERO guarded tool
children ever existed at the point of interrupt and the interrupt
still arrived. This EXONERATES the guarded-child class entirely
(T-3651's round-14 hypothesis, already falsified by CREATE_NO_WINDOW
evidence in T-3657, is now doubly dead: even removing every guarded
child does not clear the signal).

Remaining suspects, named by T-3657's own spawn audit:
  1. frob.gates's ProcessPoolExecutor preload (multiprocessing spawn
     children on win32 share the console with their parent and are
     NOT gated by FROB_DISABLE_EXEC, since they are frob's own
     internal gate workers, not a guarded tool spawn). The main-thread
     stack at the moment of interrupt is executor.submit -> t.start(),
     i.e. right when workers/pool start -- consistent with this
     hypothesis.
  2. uv itself: `uv run` is the parent process of the diag python
     child in every variant tried so far and could be delivering a
     console ctrl event at a roughly constant ~1.4s mark regardless of
     what frob does -- both variant (a) and (b) died at ~1.4-1.6s.

Round 16 = extend the diag matrix with two more discriminants, cheap
and decisive, so ONE CI run reads all four:

  Variant (c) = variant (a) but the diag python is invoked DIRECTLY,
  with NO `uv` in its ancestry -- resolve the venv's own python.exe at
  workflow time (e.g. Join-Path $env:GITHUB_WORKSPACE ".venv\Scripts\
  python.exe", or the equivalent `uv python find` resolution done
  ONCE, then Start-Process'd directly) instead of `uv run ... python`.
  If (c) is clean, uv is the sender. If (c) still gets SIGINT, uv is
  exonerated too and the remaining suspect is variant (d).

  Variant (d) = variant (a) but with frob.gates's ProcessPoolExecutor
  preload disabled for this run. If no env gate exists for the pool
  yet, ADD one: FROB_DISABLE_POOL_PRELOAD=1 (env-gated, harmless
  everywhere else, unit-tested, same posture as FROB_DISABLE_EXEC/
  FROB_DISABLE_NET in src/frob/process/_guard.py) -- when set, skip
  constructing/using the ProcessPoolExecutor pool entirely (whatever
  the safe degraded behavior is -- e.g. run process-pool gate jobs
  serially in-process, or skip that gate group with a clear
  diagnostic, mirroring how FROB_DISABLE_EXEC's kill switch degrades
  guarded_subprocess_run). Set it for variant (d)'s diag run. If (d)
  is clean, the pool children are the sender.

  Keep variants (a) and (b) unchanged so a single CI run reports all
  four outcomes together.

Fix direction once the sender is actually named (do NOT pre-emptively
"fix" either without the matrix's own evidence):
  - If the pool is named: creationflags on multiprocessing spawn
    children (a custom Popen subclass, or a monkeypatched
    _winapi.CreateProcess wrapper applying CREATE_NO_WINDOW the same
    way guarded_subprocess_run already does for guarded tool spawns),
    OR a lazy/skip preload path on win32 that avoids spawning the pool
    at all until a gate that actually needs it runs.
  - If uv is named: switch the CI Test/diag steps to invoke the venv's
    python directly instead of through `uv run`, and document why in
    ci.yml and docs/modules/process.md.

Supersedes/extends T-3657 (round 15, filed the ProcessPoolExecutor/uv
suspects and built the 2-variant matrix this ticket extends to 4).
Related: T-3651 (round 14, falsified tool-child hypothesis), T-3648
(signal logger + diag scaffolding origin), T-3589 (win32 CI
investigation lineage).

Scope: .github/workflows/ci.yml + src/frob/process/_guard.py +
src/frob/gates/__init__.py (process-pool preload only, env-gated skip
path) + src/frob/check/** (read-mostly) + tests/test_ci_workflow_matrix.py
+ tests/unit/test_process_guard.py + tests/unit/ (new gates-pool-preload
unit tests only, not tests/gates_suite/**) + docs/modules/process.md.
Explicitly OUT of scope (do not touch): src/frob/graph/cache.py,
tests/gates_suite/**, src/frob/refactor/**, tests/conftest.py.
