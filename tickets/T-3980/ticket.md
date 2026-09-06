---
id: T-3980
title: 'artifact-smoke CI red: wrong-platform core wheels (ubuntu) + doctor repo-hygiene
  coupling (macOS)'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/artifact_smoke.py
- tests/system/test_artifact_smoke.py
- .github/workflows/ci.yml
- tests/unit/test_artifact_smoke_script.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/release.md
  reason: 'scope closure: doc target and covering unit test flagged by frob ticket
    new'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_artifact_smoke_script.py
  reason: 'scope closure: doc target and covering unit test flagged by frob ticket
    new'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: 'scope closure: pre-existing doc anchors in docs/guides/release.md (in scope)
    describe these symbols'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/doctor.py
  reason: 'scope closure: pre-existing doc anchors in docs/guides/release.md (in scope)
    describe these symbols'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/doctor.py
  reason: 'reverting: docs/guides/release.md scope-closure debt is unrelated pre-existing
    content (doctor.py/verify_release_ci_status.py anchors), out of proportion to
    pull in per this repo''s established precedent (see artifact_smoke.py''s own existing
    COV001 waiver reasoning); documenting via code docstrings instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: scripts/verify_release_ci_status.py
  reason: 'reverting: docs/guides/release.md scope-closure debt is unrelated pre-existing
    content (doctor.py/verify_release_ci_status.py anchors), out of proportion to
    pull in per this repo''s established precedent (see artifact_smoke.py''s own existing
    COV001 waiver reasoning); documenting via code docstrings instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/guides/release.md
  reason: 'reverting: docs/guides/release.md scope-closure debt is unrelated pre-existing
    content (doctor.py/verify_release_ci_status.py anchors), out of proportion to
    pull in per this repo''s established precedent (see artifact_smoke.py''s own existing
    COV001 waiver reasoning); documenting via code docstrings instead'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series FU: two failures in tests/system/test_artifact_smoke.py are the only thing keeping ubuntu and macOS CI red after T-3935 landed.

1) UBUNTU: test_unbounded_mcp_pin_fails_serve_extra_check and test_current_pin_passes_serve_extra_check fail because the core wheels reaching the find-links dir (frob-core/target/wheels) are built for the wrong platform (macOS/arm64 wheels present on the ubuntu runner). Need to find the actual mechanism in .github/workflows/ci.yml (hypothesis: artifact upload/download crosses platforms) and fix so each platform job only sees wheels built for itself. Also extend _require_core_wheels in scripts/artifact_smoke.py to detect present-but-wrong-platform core wheels and fail legibly instead of surfacing uv's raw resolver trace.

2) MACOS: test_current_pin_passes_serve_extra_check base-install step runs frob doctor in a clean venv against the installed wheel, but doctor inspects the surrounding checkout (stale ticket leases, hook drift, claude config drift) and any such finding fails the artifact check. Need to make base-install assert only that the installed wheel imports and runs (binary runs, --version works, both cores import) without depending on repo hygiene of the checkout it happens to run in.