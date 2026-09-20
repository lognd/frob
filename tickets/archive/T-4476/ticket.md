---
id: T-4476
title: 'release.yml: artifact-smoke manylinux-aarch64 leg runs on an x86_64 host and
  cannot install the aarch64 wheel'
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
  reason: 'waive BUG002: TEST_ABSENT_AT_PARENT (test written for this ticket, CI-config
    change with no local repro path)'
  actor: logan
  at: '2026-09-13'
  old_length: 1338
  new_length: 2794
evidence:
- tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_smoke_runs_on_a_native_arm_image
- tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_not_in_smoke_exempt_targets
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34799974130 (tag v0.531.0 = 9bf7175b4): all five builds green and artifact-smoke PASSES on macos-arm64, manylinux-x86_64 and windows-x86_64; the only failure is "artifact-smoke (manylinux-aarch64, ubuntu-latest)": that leg runs on an x86_64 host and tries to install the aarch64 wheel, the same cross-architecture boundary T-4470 documented for macos-x86_64 (it dropped that smoke leg and marked the build entry cross: true) but left in place for manylinux-aarch64. FIX in .github/workflows/release.yml: remove the manylinux-aarch64 entry from the artifact-smoke matrix with the same PLATFORM001 comment (an x86_64 ubuntu host cannot execute an aarch64 wheel; QEMU-running Python is out of scope), or gate it on a native arm64 runner if one is available to this repo (`ubuntu-24.04-arm` is a hosted image -- prefer this if the maturin-built wheel installs there, since it keeps the smoke real; try it, and fall back to dropping the leg if the label is unavailable or the run fails for platform reasons). Update tests/unit/test_release_workflow_gate.py (test_artifact_smoke_covers_every_build_target's exemption list or the arm runner assertion) and docs/guides/release.md. ACCEPTANCE: the next release dispatch reaches upload-frob-core. Sprint v0.531.0 (release blocker). Do NOT touch upload-* jobs, environments or triggers.



frob:waive BUG002 reason="test added and fixed in the same commit (this ticket's own worktree, not a squash), so --check-repro against the ticket-start parent (29da7aae0) reports TEST_ABSENT_AT_PARENT: 'no tests ran' -- the test does not exist there at all, by construction, since it was written for this ticket. This is a CI-config change (.github/workflows/release.yml matrix os label edit) with no local runtime path to fail-before/pass-after on this host: there is no way to execute a hosted-runner-level install on either ubuntu-latest or ubuntu-24.04-arm locally. The designated node ids (TestArtifactSmokeAarch64UsesNativeArmRunner, frob:tests T-4476) assert against the REAL workflow YAML, confirming artifact-smoke's manylinux-aarch64 entry names an arm64-labeled hosted image (not ubuntu-latest) and is not added to the PLATFORM001 exemption list; they PASS post-fix and would FAIL against the pre-fix workflow (os: ubuntu-latest). The actual defect (release run 34799974130: artifact-smoke (manylinux-aarch64, ubuntu-latest) failed installing the aarch64 wheel into an x86_64 host, the identical boundary T-4470 hit and fixed for macos-x86_64) is documented in this ticket's body and in docs/guides/release.md; the fix moves that one leg to the GitHub-hosted native arm64 image ubuntu-24.04-arm (free for this public repo since GA Jan 2025) so the smoke stays a real install+execution rather than falling back to a documented-boundary drop."