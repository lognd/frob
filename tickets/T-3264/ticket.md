---
id: T-3264
title: 'TestNativeMissingFailsLoud SYS004 test: unhandled NativeExtensionUnavailable
  crashes main instead of degrading to SYS004 finding'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- src/frob/gates/_vmodel.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: T-3264's actual fix lives in _vmodel.py's unguarded import strata_core,
    not anywhere under src/frob/strata/** (that package's own guarded imports were
    already correct)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_vmodel.py
  reason: T-3264's actual fix lives in _vmodel.py's unguarded import strata_core,
    not anywhere under src/frob/strata/** (that package's own guarded imports were
    already correct)
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while root-causing T-3249's 11-failure cluster.
tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
fails deterministically (reproduces in isolation, -p no:xdist, no
concurrency needed) on unmodified main.

Expected (per the test's own docstring): frob check on a repo with
.strata files under design/, with the native strata_core extension
faked missing, exits nonzero and reports SYS004 (a loud, typed
degradation).

Actual: "main: unhandled exception during dispatch: simulated:
strata_core native extension not installed (T-0316 litmus)" -- the
NativeExtensionUnavailable raised deep in load_design_ids/
parse_module is NOT caught and converted into a SYS004 finding; it
propagates all the way to frob.__main__.main and crashes the whole
check dispatch with a raw traceback line instead of a gate result.

Repro:
  uv run pytest -q -p no:xdist tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present

Captured failure text:
  ERROR: parse_module: strata_core native extension unavailable (ImportError: simulated: strata_core native extension not installed (T-0316 litmus))
  ERROR: main: unhandled exception during dispatch: simulated: strata_core native extension not installed (T-0316 litmus)

NOT a concurrency/host-load artifact -- confirmed via direct isolated
repro before any load was applied. Out of T-3249's scope (that ticket
owns the REF001/_STAGE_GROUPS/tickets.md-exemption subset of the
11-failure cluster; this is a separate, unrelated root cause in the
native-missing degrade path).

Root cause not yet identified beyond "the exception escapes uncaught
somewhere between load_design_ids/parse_module and whatever SYS004's own
gate wraps them with" -- needs tracing which caller is supposed to catch
NativeExtensionUnavailable and currently doesn't.
