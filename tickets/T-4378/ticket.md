---
id: T-4378
title: artifact-smoke must-stay-quiet test conflates base-install toolchain PATH with
  serve-extra verdict
state: done
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_artifact_smoke.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: macOS-only PATH-dependent defect not reproducible on this
    Linux checkout'
  actor: logan
  at: '2026-09-09'
  old_length: 2295
  new_length: 2807
evidence:
- tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check
fails on macOS CI (run 34358765772):

  AssertionError: PASS serve-extra
    FAIL base-install: frob doctor: frob doctor
    ...
    remediation: required tool(s) missing: ruff not found -- pip install ruff
    (or: uv pip install ruff); ty not found -- pip install ty (or: uv pip
    install ty)
    artifact-smoke: 1 of 2 check(s) FAILED
  assert 1 == 0

The test asserts result.returncode == 0 for the WHOLE artifact_smoke.py
invocation ("--wheel ... --core-wheels-dir ... --skip-native"), which runs
both check_base_install and check_serve_extra. check_base_install shells
out to frob doctor inside a bare fresh venv, and doctor's external-tool
inventory (T-3276, src/frob/doctor.py scan_external_tools/_doctor_healthy)
marks the run unhealthy whenever ruff/ty are not resolvable on the
AMBIENT PATH of whatever machine runs the test -- an environment fact
about the CI runner, not about whether the wheel under test
installs/imports correctly. check_base_install's own docstring already
scopes itself to entry-point wiring plus native-extension import status,
not ambient toolchain presence -- so this is scope creep the check was
never meant to gate on, and this specific TEST's own name/docstring only
promises the serve-extra check passes cleanly, not base-install.

Contract decision (per brief): the artifact smoke test proves the WHEEL
imports and serves; this specific must-stay-quiet test's assertion should
check the serve-extra verdict, not the whole doctor health / overall
script exit code. Do NOT weaken scripts/artifact_smoke.py itself or
src/frob/doctor.py -- the smoke gate stays a hard, unmodified check of
the wheel for the real .github/workflows/release.yml upload gate
(T-3884's alpha-blocker status). This is a test-only fix in
tests/system/test_artifact_smoke.py.

Plan: change test_current_pin_passes_serve_extra_check to assert on the
serve-extra PASS/FAIL markers in stdout instead of the process
returncode, with a docstring explaining why base-install's toolchain
finding is out of this test's scope.

Verify: uv run pytest tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check -x -q -p no:xdist


frob:waive BUG002 reason="macOS-only defect (frob doctor reports base-install unhealthy only when ruff/ty are absent from the CI runners ambient PATH) -- unreproducible on this Linux dev checkout where ruff/ty ARE on PATH, so the bound test passes at both main and the fix here regardless. Fix is test-only, a direct read of check_base_installs own documented scope (entry-point wiring plus native-extension import status, not ambient toolchain presence) against what the failing assertion actually checked."