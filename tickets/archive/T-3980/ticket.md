---
id: T-3980
title: 'artifact-smoke CI red: wrong-platform core wheels (ubuntu) + doctor repo-hygiene
  coupling (macOS)'
state: done
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
- docs/guides/release.md
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
- op: add
  glob: docs/guides/release.md
  reason: 'AFFECT001: check_base_install''s frob:doc target changed and must be updated;
    doctor.py/verify_release_ci_status.py added only to close release.md''s pre-existing
    unrelated doc-anchor scope debt (no edits planned to those two files)'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/doctor.py
  reason: 'AFFECT001: check_base_install''s frob:doc target changed and must be updated;
    doctor.py/verify_release_ci_status.py added only to close release.md''s pre-existing
    unrelated doc-anchor scope debt (no edits planned to those two files)'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: 'AFFECT001: check_base_install''s frob:doc target changed and must be updated;
    doctor.py/verify_release_ci_status.py added only to close release.md''s pre-existing
    unrelated doc-anchor scope debt (no edits planned to those two files)'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/doctor.py
  reason: 'reverting: pulling doctor.py into scope cascades into 99+ unrelated pre-existing
    doc-anchor/test-coverage symbols (docs/guides/install.md, docs/modules/cli.md,
    tests/test_doctor.py, tests/unit/test_doctor.py, tests/unit/test_verify_release_ci_status.py)
    that have nothing to do with T-3980; keeping only docs/guides/release.md in scope
    to satisfy AFFECT001 on check_base_install, accepting the 2 pre-existing SCOPE002
    findings on release.md''s OTHER anchors (doctor.py/verify_release_ci_status.py,
    both pre-dating T-3980) as known debt -- matches T-3935''s own precedent of declining
    to fully close this shared doc''s scope'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: scripts/verify_release_ci_status.py
  reason: 'reverting: pulling doctor.py into scope cascades into 99+ unrelated pre-existing
    doc-anchor/test-coverage symbols (docs/guides/install.md, docs/modules/cli.md,
    tests/test_doctor.py, tests/unit/test_doctor.py, tests/unit/test_verify_release_ci_status.py)
    that have nothing to do with T-3980; keeping only docs/guides/release.md in scope
    to satisfy AFFECT001 on check_base_install, accepting the 2 pre-existing SCOPE002
    findings on release.md''s OTHER anchors (doctor.py/verify_release_ci_status.py,
    both pre-dating T-3980) as known debt -- matches T-3935''s own precedent of declining
    to fully close this shared doc''s scope'
  actor: logan
  at: '2026-09-06'
evidence:
- tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall::test_doctor_runs_outside_work_dir_not_process_cwd
- tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_wrong_platform_wheel_names_the_mismatch
- tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_matching_platform_wheel_does_not_raise
- tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_wheel_matches_host_platform_rejects_foreign_tag
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