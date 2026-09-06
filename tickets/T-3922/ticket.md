---
id: T-3922
title: none of frob's eight third-party GitHub Actions are SHA-pinned, including the
  one that publishes to PyPI
state: done
kind: security
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
- .github/workflows/**
- .github/dependabot.yml
- tests/test_ci_workflow_actions_pinned.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .github/workflows/**
  reason: 'Part A: pin third-party GitHub Actions to SHAs in workflow files'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: .github/dependabot.yml
  reason: 'Part A: add GitHub Actions update mechanism (Dependabot) alongside SHA
    pins'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_ci_workflow_actions_pinned.py
  reason: 'add a repro test proving the SHA-pin fix: fails against an unpinned uses:
    line, passes against the pinned workflow'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: design/frob.strata
  reason: declare tests/test_ci_workflow_actions_pinned.py's fs.read effect (Path.read_text
    on the workflow yaml) in the testsuite node's via-list, required by SELFAUDIT001/SYS100
  actor: logan
  at: '2026-09-05'
evidence:
- tests/unit/test_release_workflow_gate.py::TestReleaseWorkflowNoAutomaticTrigger::test_ci_workflow_never_references_release_or_pypi
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
- tests/test_ci_workflow_timeout.py::TestBuildJobHasATimeoutBackstop::test_build_job_declares_timeout_minutes
- tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_wraps_pytest_in_timeout_abrt
- tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_uses_are_all_sha_pinned
- tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_release_workflow_uses_are_all_sha_pinned
- tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_yaml_still_parses
- tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_release_workflow_yaml_still_parses
designated_repro_test: tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_uses_are_all_sha_pinned
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED IN THIS REPO 2026-09-05, after applying a consumer audit's lesson to
ourselves. NONE of frob's third-party GitHub Actions are SHA-pinned:

    uses: PyO3/maturin-action@v1
    uses: actions/cache@v4
    uses: actions/checkout@v4
    uses: actions/download-artifact@v4
    uses: actions/upload-artifact@v4
    uses: astral-sh/setup-uv@v5
    uses: dtolnay/rust-toolchain@stable
    uses: pypa/gh-action-pypi-publish@release/v1

    SHA-pinned (40-hex): 0 of 8

EVERY ONE IS A MUTABLE REFERENCE. A tag can be moved; a branch moves by
definition. `@stable` and `@release/v1` are branches.

WHY THIS IS RELEASE-PATH SECURITY AND NOT HYGIENE:
  - `pypa/gh-action-pypi-publish@release/v1` is THE ACTION THAT PUBLISHES TO
    PyPI, and the release workflow uses OIDC trusted publishing -- so that
    action runs in a job holding the credential that can publish frob. A moved
    branch there is arbitrary code with our publishing identity.
  - `dtolnay/rust-toolchain@stable` builds the NATIVE EXTENSIONS that
    T-3845 just made default dependencies for every consumer. Compromised
    toolchain setup means compromised wheels, shipped to everyone, signed by
    our pipeline.
  - `PyO3/maturin-action@v1` builds those wheels.
The blast radius is not this repo; it is every consumer who installs frob.

ORIGIN: consumer audit lesson (logand.app-v2 F-109..F-117 item 4), which
observed that `.github/workflows/*.yml` is a DEPENDENCY MANIFEST frob exempts
from everything, while frob.toml already treats uv.lock / package-lock.json /
Cargo.lock as vetted entrypoints. Their proposed rule -- "every non-first-party
`uses:` must be a 40-hex SHA" -- is cheap and total. I checked frob against it
rather than assuming we were fine; we are not.

TWO PIECES OF WORK, and the first should not wait for the second:

  A. PIN THIS REPO'S ACTIONS. Replace each mutable ref with a 40-hex SHA plus a
     trailing comment naming the version it corresponds to (the conventional
     form, so upgrades stay legible). Decide explicitly whether first-party
     `actions/*` are in scope -- GitHub's own are lower risk but not zero, and
     "non-first-party only" is a defensible line if stated.
     ORDER MATTERS FOR THE ALPHA: the release workflow is what publishes it. If
     the alpha is cut before this lands, it is published by unpinned actions.
     That is a decision for the owner, not a default.

  B. EXTEND `frob vet` TO WORKFLOW `uses:` REFERENCES, so this cannot regress
     and so consumers get it too. frob vet already reasons about lockfiles as
     vetted entrypoints; a workflow file is the same kind of artifact --
     third-party code pinned by reference. Add the SHA requirement as a rule
     with an allowlist for first-party if that is the chosen line.

CAUTION ON (A): pinning to a SHA freezes security PATCHES too. The mitigation
is the trailing version comment plus a renovate-style update path, not leaving
it mutable. Say which update mechanism is expected, or the pins rot and someone
un-pins them in six months to fix a build.

MUST-FIRE FIXTURE (for B): a workflow with a tag-pinned non-first-party `uses:`
is flagged.
MUST-STAY-QUIET: a 40-hex SHA pin passes; a first-party action passes if that
is the chosen line.

ACCEPTANCE
- All eight refs pinned, or a stated, reasoned exemption per ref.
- The first-party question answered explicitly.
- The update mechanism named.
- If (B) lands, the fixtures committed.