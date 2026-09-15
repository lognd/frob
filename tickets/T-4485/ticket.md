---
id: T-4485
title: rename the strata kernel distribution strata-core -> frob-strata (PyPI name
  taken); keep crate dir and strata_core import
state: done
kind: feature
origin: agent
created: '2026-09-14'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/pyproject.toml
- pyproject.toml
- uv.lock
- .github/workflows/release.yml
- .github/workflows/ci.yml
- scripts/artifact_smoke.py
- src/frob/gates/_version_coupling.py
- src/frob/graph/cache.py
- tests/unit/test_release_workflow_gate.py
- tests/unit/gates/test_version_coupling.py
- tests/system/test_artifact_smoke.py
- tests/system/test_public_api_from_wheel.py
- tests/test_graph.py
- docs/guides/release.md
- docs/guides/install.md
- docs/modules/gates.md
- README.md
- Makefile
- tests/unit/test_artifact_smoke_script.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_artifact_smoke_script.py
  reason: the smoke script's required-wheel glob renamed to frob_strata-*.whl, so
    its unit fixtures must create wheels by the new name
  actor: logan
  at: '2026-09-14'
evidence:
- tests/unit/test_artifact_smoke_script.py::TestReadCorePins::test_reads_both_pins_from_metadata
- tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_matched_versions_clean
- tests/unit/test_release_workflow_gate.py::TestUploadSplitPerDistribution::test_application_upload_needs_both_kernel_uploads
designated_repro_test: null
threat: null
component: release
anchor: false
anchor_reason: null
land_commit: null
---
## Why

The PyPI project name strata-core is already taken by another owner, so
the strata kernel cannot be published under it. Owner decision 2026-09-15:
publish it as frob-strata. Both release runs on tag v0.531.0 today reached
upload-strata-core and failed on the missing publisher; the publisher can
only be registered once the distribution name is one we can own.

## Scope of the rename (distribution name ONLY)

Changes: the distribution name strata-core -> frob-strata everywhere it is
the PyPI/dependency name -- strata-core/pyproject.toml [project].name,
root pyproject.toml pins ([project].dependencies, the native extra,
[tool.uv.sources] key), uv.lock (regenerated), release.yml (job
upload-frob-strata, environment pypi-frob-strata, wheel/sdist display
names), ci.yml step names, scripts/artifact_smoke.py's required-wheel map
and Requires-Dist pin reader, VERSION001's dependency-name table,
frob.graph.cache's importlib.metadata fingerprint package, the tests that
pin those names, and the release/install docs.

Stays: the strata-core/ crate directory, the Cargo package and lib names,
the strata_core Python import name (maturin module-name), every path-shaped
mention, and the frob-core kernel.

The GitHub environment pypi-frob-strata already exists (created 2026-09-15,
no required reviewer, matching the pypi-frob-core posture). pypi-strata-core
is deleted once this lands.

## Acceptance

- uv build in strata-core/ produces frob_strata-<v>-*.whl whose METADATA
  Name is frob-strata; maturin still exposes import strata_core.
- frob's own wheel METADATA carries Requires-Dist: frob-strata==<v>.
- frob check --only release and VERSION001 pass with the new pin name.
- test_release_workflow_gate, test_version_coupling, test_artifact_smoke
  and test_graph pass with the new names.