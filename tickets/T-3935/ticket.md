---
id: T-3935
title: 'ALPHA BLOCKER: frob wheel is uninstallable -- frob-core/strata-core hard-pinned
  but in no registry'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- .github/workflows/release.yml
- scripts/artifact_smoke.py
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
MEASURED in CI run 34005559354. The standalone-install job fails outright:

  Because frob-core was not found in the package registry and
  frob==0.530.0 depends on frob-core==0.530.0, we can conclude that
  frob==0.530.0 cannot be used.

and the same cause reds three tests in tests/system/test_artifact_smoke.py on ubuntu and macOS (macOS names strata-core for macosx_11_0_arm64).

CAUSE. T-3845 made the two maturin cores DEFAULT dependencies with a hard == pin. That is the right dependency shape, but neither core is published anywhere, so any resolution that goes to a registry cannot succeed. Building the pure-python wheel is not enough: nothing in CI builds or supplies the core wheels to the installing resolver.

THIS IS EXACTLY THE STANDING ALPHA REQUIREMENT: the strata-core and frob-core maturin packages must be wheeled and grabbed automatically whenever a release is cut. Today they are neither.

WHAT TO BUILD.
1. Build both core wheels for the target platform in CI before any install-the-artifact step, and point the installing resolver at them (a local find-links index over the built dist, not a network registry).
2. Apply the same in the release workflow so a cut release ships core wheels alongside the frob wheel. artifact-smoke must prove the REAL install path; right now it proves a path no consumer can follow.
3. artifact_smoke.py must fail with a message that NAMES the missing core and says it was not supplied, rather than surfacing a raw resolver trace. A smoke check that cannot distinguish 'core not built' from 'pin is wrong' is a silent zero in the release gate.

DO NOT fix this by loosening the == pin or moving the cores back to an extra. The pin is deliberate (T-3845) and the coupling is real; the defect is that CI never supplies what the pin demands.

ACCEPTANCE
- standalone-install passes on ubuntu.
- The three artifact-smoke tests pass on ubuntu and macOS.
- The release workflow produces core wheels as published artifacts, verified by inspecting the workflow's artifact list -- do not reason about it.
- A must-fire fixture: a smoke run with the cores deliberately absent reports the named core as missing.