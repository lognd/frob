---
id: T-4470
title: 'release.yml: macos-x86_64 build pinned to the retired macos-13 runner never
  schedules and blocks the release concurrency group'
state: done
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
- .github/workflows/release.yml
- tests/unit/test_release_workflow_gate.py
- docs/guides/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: CI-config change has no local fail-before/pass-after repro
    path'
  actor: logan
  at: '2026-09-13'
  old_length: 1675
  new_length: 2780
evidence:
- tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_artifact_smoke_covers_every_build_target
- tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_no_matrix_entry_uses_a_retired_image
- tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_build_and_artifact_smoke_jobs_have_timeout_minutes
- tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_expected_targets_are_marked_cross
- tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_native_targets_are_not_marked_cross
- tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_import_smoke_step_branches_on_matrix_cross
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34769124533 (2026-09-13) sat in `queued` for over four hours on the job "build (macos-x86_64, macos-13, x86_64-apple-darwin, off)": GitHub retired the macos-13 hosted runner image (announced for removal in late 2025), so the label never gets a runner, the job never starts, and -- because release.yml declares `concurrency: group: release, cancel-in-progress: false` -- every later dispatch (34781548188) queues behind it forever. The four other targets (manylinux x86_64/aarch64 after T-4464, macos-arm64, windows) build fine. FIX in .github/workflows/release.yml: build the x86_64-apple-darwin wheels on `macos-latest` (arm64 host) by cross-compiling -- maturin-action supports `target: x86_64-apple-darwin` on an arm64 macOS runner (rustup adds the target; the abi3 wheel needs no x86_64 Python), or produce a `universal2` wheel from the macos-arm64 job and drop the separate x86_64 job; keep the import-smoke step meaningful (on an arm64 host it cannot import an x86_64 wheel -- skip the import for cross-built targets with an explicit comment, or run it under Rosetta `arch -x86_64` if a x86_64 Python is available). Also add `timeout-minutes` to the build matrix jobs so an unschedulable job fails instead of holding the release group. tests/unit/test_release_workflow_gate.py: assert no matrix entry uses a retired image label (macos-13, macos-12, ubuntu-20.04, windows-2019) and that every build job has timeout-minutes. docs/guides/release.md: note the cross-build. ACCEPTANCE: a dispatch of release.yml builds all five targets green and reaches the upload jobs. Sprint v0.531.0 (release blocker). Do NOT touch any upload-* job, environment, or trigger.



frob:waive BUG002 reason="this is a CI-config change (.github/workflows/release.yml matrix os/timeout edits plus a docs note) with no runtime code path to fail-before/pass-after on this host: there is no local execution of a GitHub-hosted-runner scheduling decision to repro. The designated node ids (tests/unit/test_release_workflow_gate.py, all classes) assert against the REAL workflow YAML in this repo (frob:tests T-4470) and PASS post-fix, confirming no matrix entry uses a retired image label and both build/artifact-smoke declare timeout-minutes; they necessarily also pass at any prior commit that happened to avoid the specific macos-13 regression, so they are confirmatory-only by construction, not by omission. The actual defect (release run 34769124533 queued 4h18m against macos-13, blocking dispatch 34781548188 behind concurrency: group: release) is documented in this ticket's body and in docs/guides/release.md; the fix is verified by YAML validity (python yaml.safe_load) plus the new TestNoRetiredRunnerImages assertions, which would have failed against the pre-fix workflow file."