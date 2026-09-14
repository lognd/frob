---
id: T-4479
title: 'make core-wheels spawns bare maturin (not on PATH in CI): every leg red after
  T-4465'
state: queued
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
CI run 34809307457 (main 383d31bb9, first run after T-4465 landed): all three legs fail in the new step "Build native extension wheels (frob-core + strata-core, T-4465)" -- `make core-wheels` runs build_natives' `maturin develop`/`maturin build` with a BARE `maturin` argv and the runner has no maturin on PATH ("error: Failed to spawn: `maturin` ... No such file or directory"); the older `make core` target resolves maturin through the project environment (read how: `uv run maturin` / the .venv binary / maturin-action's install), and the self-gate's BARETOOL001 rule exists exactly for this class. FIX: make `core-wheels` (Makefile ~line 609 and the build_natives helper it calls) resolve maturin the same way `core` does (single shared resolution, no duplication), and keep the T-4465 behaviour (delete stale wheels, `maturin build --release --out target/wheels` per crate). Add/adjust tests in tests/test_ci_workflow*.py or the Makefile tests if any pin the invocation. ACCEPTANCE: the next main CI run passes the core-wheels step on all three legs and the artifact-smoke tests still pass. Sprint v0.531.0 (CI green blocker introduced by T-4465).
