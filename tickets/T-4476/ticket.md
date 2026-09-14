---
id: T-4476
title: 'release.yml: artifact-smoke manylinux-aarch64 leg runs on an x86_64 host and
  cannot install the aarch64 wheel'
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
- .github/workflows/release.yml
- tests/unit/test_release_workflow_gate.py
- docs/guides/release.md
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
Release run 34799974130 (tag v0.531.0 = 9bf7175b4): all five builds green and artifact-smoke PASSES on macos-arm64, manylinux-x86_64 and windows-x86_64; the only failure is "artifact-smoke (manylinux-aarch64, ubuntu-latest)": that leg runs on an x86_64 host and tries to install the aarch64 wheel, the same cross-architecture boundary T-4470 documented for macos-x86_64 (it dropped that smoke leg and marked the build entry cross: true) but left in place for manylinux-aarch64. FIX in .github/workflows/release.yml: remove the manylinux-aarch64 entry from the artifact-smoke matrix with the same PLATFORM001 comment (an x86_64 ubuntu host cannot execute an aarch64 wheel; QEMU-running Python is out of scope), or gate it on a native arm64 runner if one is available to this repo (`ubuntu-24.04-arm` is a hosted image -- prefer this if the maturin-built wheel installs there, since it keeps the smoke real; try it, and fall back to dropping the leg if the label is unavailable or the run fails for platform reasons). Update tests/unit/test_release_workflow_gate.py (test_artifact_smoke_covers_every_build_target's exemption list or the arm runner assertion) and docs/guides/release.md. ACCEPTANCE: the next release dispatch reaches upload-frob-core. Sprint v0.531.0 (release blocker). Do NOT touch upload-* jobs, environments or triggers.
