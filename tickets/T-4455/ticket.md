---
id: T-4455
title: 'Windows CI: tests spawn ''bash'' and get the WSL System32 stub (UTF-16 ''no
  installed distributions''), not Git Bash'
state: in-progress
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_worktree_guard.py
- tests/helpers/*.py
- tests/conftest.py
- tests/unit/test_helpers_bash*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_helpers_bash.py::test_non_windows_returns_plain_bash
- tests/unit/test_helpers_bash.py::test_prefers_git_bash_over_system32_stub
- tests/unit/test_helpers_bash.py::test_system32_stub_only_skips
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on the GitHub Windows runner (CI run 34735688390, head 04056abd0, which INCLUDES T-4446's UTF-8 stdout fix): tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering still fails with returncode=1, stderr='' and a UTF-16LE (NUL-interleaved) STDOUT whose decoded tail reads "...<Distro>' to install." That is the Windows Subsystem for Linux launcher's message ("Windows Subsystem for Linux has no installed distributions ... 'wsl.exe --install <Distro>' to install."), printed in UTF-16 by C:\Windows\System32\bash.exe. The test spawns ["bash", "-c", script]; on windows-latest PATH resolution from the pytest process picks System32\bash.exe (the WSL stub) ahead of Git Bash, so the script never runs at all -- frob agent env is never invoked, which is why T-4405/T-4446 (stdout encoding of frob agent env) could not fix it and why the winrun mirror (Git Bash first on PATH, or no WSL stub) passes. FIX (test-only, plus any shared helper): resolve the bash binary explicitly on win32 -- prefer Git for Windows' bash (probe in order: $env:ProgramFiles\Git\bin\bash.exe, $env:ProgramFiles\Git\usr\bin\bash.exe, the bash next to `git` from shutil.which("git")), never System32\bash.exe; skip with a clear reason if none exists. Apply the same resolver to every test in tests/ that spawns "bash" (git grep -n '"bash"' tests) via one helper (tests/helpers or tests/conftest.py), not per-file copies (NO DUPLICATION). Add a unit test for the resolver that simulates a PATH where System32 comes first. ACCEPTANCE: (1) the resolver never returns a path under System32; (2) test_bare_eval_succeeds_with_no_filtering and its 4 siblings pass on the winrun mirror; (3) the node id passes on the next Windows CI run. Sprint v0.531.0 (last known Windows test failure). Supersedes the premise of T-4405/T-4446 for this node id (T-4446's UTF-8 forcing stays, it is correct for the agent-env output itself).
