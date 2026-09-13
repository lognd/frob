---
id: T-4465
title: 'CI artifact-smoke resolves kernels from stale cached target/wheels: unsatisfiable
  frob-core==0.531.0 after the bump'
state: queued
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- Makefile
- scripts/artifact_smoke.py
- tests/unit/test_artifact_smoke_script.py
- tests/test_ci_workflow*.py
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
CI run 34768157963 (head bce3e74f9, the first run after the 0.531.0 version bump abd79f23f), ubuntu AND macOS Test steps: exactly two failures, both in tests/system/test_artifact_smoke.py (TestArtifactSmokeMustFire::test_unbounded_mcp_pin_fails_serve_extra_check and TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check). scripts/artifact_smoke.py's base-install check pip-installs the freshly built frob-0.531.0 wheel with `--find-links <repo>/frob-core/target/wheels` and `<repo>/strata-core/target/wheels` as the ONLY source for the pinned kernels (frob-core==0.531.0, strata-core==0.531.0), and uv reports "your requirements are unsatisfiable": the wheels under target/wheels are the stale frob_core-0.530.0-*.whl / strata_core-0.530.0-*.whl restored from the actions/cache entry for the target directories (cache key = hash of the two Cargo.lock files, which the version bump did not change), and ci.yml's `make core` step (maturin develop) refreshes the editable install but not target/wheels. The same test passed on every run before the bump only because the cached wheel version happened to equal the pin. This is a stale-derived-artifact silent-pass: the smoke test measured whatever the cache held. FIX (all three, no duplication): (1) ci.yml's native-build step (or `make core`) must produce wheels for the CURRENT crate version into target/wheels every run (a `maturin build --release --out target/wheels` per crate, or delete stale wheels first), and the cache key for the target dirs must include the crate versions (hashFiles of frob-core/pyproject.toml and strata-core/pyproject.toml, or the version string); (2) scripts/artifact_smoke.py::_require_core_wheels must select only wheels whose version equals the pin it is about to install and fail loudly naming the stale versions it found (today's glob frob_core-*.whl is version-blind); (3) tests/unit/test_artifact_smoke_script.py covers the version-mismatch case. ACCEPTANCE: the two node ids pass on the next posix run at version 0.531.0; the unit test fails against the old glob. Sprint v0.531.0 (CI green blocker introduced by the release bump). Related: T-3884 (artifact smoke gate), the derived-artifact-trap lesson.
