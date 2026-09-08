---
id: T-4297
title: frob.app.profile_runner_run is advertised in __all__ but AssertionErrors on
  first access
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/__init__.py
- tests/unit/test_app_lazy_exports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_lazy_exports.py
  reason: the fix's own regression test belongs alongside the existing lazy-runner-alias
    test suite
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while building T-4150's wheel-import test (tests/system/test_public_api_from_wheel.py), which imports every name literally listed in every package's __all__ against a real install.

src/frob/app/__init__.py's _RUNNER_RUN_MODULES dict (line ~90) maps 'profile_runner_run' -> 'profile_runner', and 'profile_runner_run' is listed in __all__ (line ~250). But _import_runner_run_module's closed if/elif chain (T-1337's OPAQUE001 workaround) has no 'profile_runner' branch -- it jumps from 'pool_runner' straight to 'registry_runner'. Accessing frob.app.profile_runner_run (the PEP 562 module __getattr__ path) hits the chain's else-branch and raises AssertionError('_import_runner_run_module: unknown runner module name profile_runner'), not the module.

Reproduce directly against this tree (no wheel needed -- this is a source-tree bug, not a packaging one):

  python -c "import frob.app; frob.app.profile_runner_run"

This is the same missing-registration-list class of defect docs/modules/gates.md's 'Registering a new gate' section already documents for a different multi-list surface (T-4163) -- a new/renamed runner module apparently reached _RUNNER_RUN_MODULES and __all__ but not this chain. tests/unit/test_app_lazy_exports.py only exercises 'one alias' generically and evidently never happened to pick profile_runner_run, so this shipped unnoticed.

Fix: add the missing 'elif module_name == "profile_runner": import frob.app.profile_runner as module' branch (matching the existing chain's pattern), and consider a regression test that walks _RUNNER_RUN_MODULES exhaustively rather than spot-checking one alias, so a future addition to the dict without a matching chain branch fails immediately.