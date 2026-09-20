---
id: T-4479
title: 'make core-wheels spawns bare maturin (not on PATH in CI): every leg red after
  T-4465'
state: done
kind: bug
origin: agent
created: '2026-09-14'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- Makefile
- .github/workflows/ci.yml
- tests/test_ci_workflow*.py
- scripts/build_natives*.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the new test file's fs.read capability on
    the testsuite node in design/frob.strata; a one-line addition to an existing via=
    list, not a new capability grant
  actor: logan
  at: '2026-09-14'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS111 requires bumping the testsuite::fs.read ratchet ceiling
    alongside the design/frob.strata via-list addition, same one-count-bump pattern
    every prior test-file addition to this node has made
  actor: logan
  at: '2026-09-14'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS111 requires bumping the testsuite::fs.read ratchet ceiling
    alongside the design/frob.strata via-list addition
  actor: logan
  at: '2026-09-14'
evidence:
- tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_invokes_uvx_maturin
- tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_does_not_invoke_uv_run_maturin
- tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_does_not_invoke_bare_maturin
- tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_still_rebuilds_target_wheels_per_crate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34809307457 (main 383d31bb9, first run after T-4465 landed): all three legs fail in the new step "Build native extension wheels (frob-core + strata-core, T-4465)" -- `make core-wheels` runs build_natives' `maturin develop`/`maturin build` with a BARE `maturin` argv and the runner has no maturin on PATH ("error: Failed to spawn: `maturin` ... No such file or directory"); the older `make core` target resolves maturin through the project environment (read how: `uv run maturin` / the .venv binary / maturin-action's install), and the self-gate's BARETOOL001 rule exists exactly for this class. FIX: make `core-wheels` (Makefile ~line 609 and the build_natives helper it calls) resolve maturin the same way `core` does (single shared resolution, no duplication), and keep the T-4465 behaviour (delete stale wheels, `maturin build --release --out target/wheels` per crate). Add/adjust tests in tests/test_ci_workflow*.py or the Makefile tests if any pin the invocation. ACCEPTANCE: the next main CI run passes the core-wheels step on all three legs and the artifact-smoke tests still pass. Sprint v0.531.0 (CI green blocker introduced by T-4465).