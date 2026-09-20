---
id: T-4473
title: artifact-smoke native-extra runs frob doctor inside the repo checkout; fails
  on hooks/claude drift/detached HEAD/import-source, not the wheel
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
- scripts/artifact_smoke.py
- tests/unit/test_artifact_smoke_script.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4709: preserve 109-column land-block detail trimmed from _fmt_directives.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1870
  new_length: 2301
evidence:
- tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra::test_doctor_runs_outside_work_dir_not_process_cwd
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Release run 34789841956 (tag v0.531.0 = 66028f99c): all five wheel builds green for the first time; then artifact-smoke FAILED on all four legs in "Run the artifact smoke stage (T-3884)": `FAIL native-extra: frob doctor (native)` -- "frob doctor found issue(s)" with remediation lines for managed git hooks missing in the CI checkout (.git/hooks/pre-commit etc., `frob scaffold apply`), Claude config DRIFT (10 managed files differ from ~/.claude on the runner), unlanded-work scan git failures (`git diff main...` under a detached HEAD at the tag: no `main` ref), and T-4459's new import-source check ("import frob resolves to .../venv-native/site-packages/frob/__init__.py, not this checkout's own src/frob/__init__.py"). Every one of these is a property of the RUNNER'S REPO CHECKOUT, not of the wheel: scripts/artifact_smoke.py::check_native_extra runs `_run_module(python, "doctor", name="frob doctor (native)")` with the process cwd (the checkout), whereas the base check `_version_and_doctor` already runs doctor with `cwd=doctor_cwd` (a scratch directory, T-3980) for exactly this reason. FIX: (1) run the native doctor from the same scratch cwd as the base check (share the helper, no duplicated code), so it inspects the installed wheel and its natives, not the repository; (2) unit test in tests/unit/test_artifact_smoke_script.py asserting check_native_extra passes cwd=<scratch> to the doctor run (mock _run_module and inspect the kwarg) and never the checkout; (3) if `frob doctor` from a scratch cwd still reports the T-4459 import-source mismatch (it should not: no checkout src exists there), report it in the Done report rather than weakening the doctor. ACCEPTANCE: the next release dispatch passes artifact-smoke on all four legs and reaches upload-frob-core. Sprint v0.531.0 (release blocker). Do NOT touch release.yml's upload jobs or environments.


T-4709 follow-up (condensed from a comment in src/frob/gates/
_fmt_directives.py's directive-wrap fallback, trimmed for DOCARCH002's
12-line cap): the marker check is `marker == "#"`, the only `#`-comment
language `_MARKERS` maps at all (E501 is a ruff/Python-specific rule).
The concrete refusal T-4473 hit twice: a directive canonicalized
mid-land into a 109-column line, land's own pre-land `ruff check` then
blocking on it.