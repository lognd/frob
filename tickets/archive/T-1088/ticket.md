---
id: T-1088
title: implement 5 statically-detectable-only SC-* supply-chain detectors with no
  enforcing check today
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
- docs/modules/vet.md
- tests/test_vet.py
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_vet.py
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_waive.py
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: detectors need docs.modules/vet.md + tests/test_vet.py updates per playbook;
    new VET007-010 rule ids need registering in gates/_waive.py's hand-maintained
    REG002 known-id list and check-coverage.yaml's CHK-GATE-VET0xx entries, same pattern
    T-1101 used for its own new VET ids
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_exact_pin_not_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_package_json_wildcard_flagged
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_cargo_toml_caret_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_traversal_data_files_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_package_relative_data_files_not_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_no_setup_py_not_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_full_sha_ref_not_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_no_workflows_dir_not_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_so_with_nearby_cargo_toml_not_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_no_binary_files_not_flagged
designated_repro_test: null
threat: null
component: null
---
Five supply-chain.yaml entries are tagged checkability:['statically-detectable']
ONLY (no requires-external-data, no process-only) but have no enforcing
detector in src/frob/vet/ today -- found while reconciling T-0721's 39
deferred:T-0721 entries:

- SC-ATTACK-UNPINNED-DEPENDENCIES: a lockfile/manifest dependency spec with
  no pin (e.g. a `*`/caret/range spec instead of an exact version) is a
  purely structural property of the manifest text.
- SC-DETECTION-PYTHON-INSTALL-ARTIFACTS: setup.py/setup.cfg/pyproject.toml
  build-backend artifacts a malicious sdist could smuggle (data_files
  writing outside the package, a cmdclass hook already tracked separately
  as install-hook capability, but the broader "installed artifact ends up
  somewhere unexpected" shape is not).
- SC-DETECTION-NPM-NON-REGISTRY-SOURCE: a package.json dependency spec
  pointing at a git/tarball/local-path source instead of a registry
  version range is a structural property of the manifest text.
- SC-DETECTION-UNPINNED-CI-ACTION: a GitHub Actions `uses: owner/action@ref`
  where `ref` is a mutable branch/tag (not a full commit SHA) is a
  structural property of tracked `.github/workflows/*.yaml`.
- SC-DETECTION-OPAQUE-BINARY-ARTIFACT: a tracked binary blob (.whl/.so/
  .node/.wasm and similar) committed directly into source control with no
  accompanying build recipe is a structural property of the tracked file
  tree.

Each needs either a real detector in src/frob/vet/ (then handled_by:<rule>)
or, on closer investigation, a reasoned disposition explaining why it is
NOT actually structurally checkable after all (narrower than it first
looks). Do not leave any of the five at a bare `deferred` pointing back
here without investigating first.