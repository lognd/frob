---
id: T-4430
title: 'uv-only-PATH test fixture unspawnable on Windows: symlink named ''uv'' has
  no .exe extension'
state: in-progress
kind: bug
origin: human
created: '2026-09-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
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
Split from T-4367 (failed there: wrong premise, out of that ticket's scope).

CI run 34596432592, Windows leg only. Node id:
tests/system/test_cli_check.py::TestCheckRuffAbsentFromTargetProject::test_missing_ruff_reports_unmeasured_not_error

MEASURED on the winrun mirror (win32): the underlying classifier is fine --
tests/unit/test_check.py::TestRunRuffToolAbsent (mocked subprocess, exercises
_run_ruff's FileNotFoundError -> tool_unavailable_result and the T-4354
tool_absent_from_project stderr-matched path directly) PASSES on win32. The
system test's own PATH-restriction fixture is what's broken:

_only_uv_on_path (tests/system/test_cli_check.py:285) does:
    (bindir / "uv").symlink_to(uv_path)

i.e. creates a symlink literally named "uv" (no .exe extension) pointing at
the real uv binary, then sets PATH to just that directory. On POSIX this
resolves fine. On Windows, CreateProcess's PATH search for an extensionless
application name appends ".exe" and looks for "uv.exe" -- it never matches a
file literally named "uv", even one whose target is uv.exe. So on win32 uv
itself is genuinely unspawnable via this fixture (WinError 2, "The system
cannot find the file specified"), which correctly and legitimately hits
_run_ruff's FileNotFoundError -> tool_unavailable_result hard-error branch
for a truly-absent uv -- the test is not exercising "uv present, ruff
absent" on Windows at all, it is accidentally exercising "uv absent" and
then asserting on the wrong expectation.

FIX: make _only_uv_on_path create a Windows-resolvable stand-in for uv,
sys.platform-branched with a declared reason -- e.g. name the symlink/copy
"uv.exe" on win32 (matching the extension CreateProcess's search requires),
posix path unchanged. Verify fail-before/pass-after on the winrun mirror
(single shared mirror checkout -- serialize against other Windows-verifying
tickets). Do not weaken the assertion itself (returncode == 0, "tool
unavailable" text) -- only the fixture's binary-naming needs the platform
branch.