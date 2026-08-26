---
id: T-2969
title: Audit remaining test_cli_*.py fixtures for the same missing-git-init pattern
  as T-2943
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_arch.py
- tests/system/test_cli_dup.py
- tests/system/test_cli_exports.py
- tests/system/test_cli_map.py
- tests/system/test_cli_outline.py
- tests/system/test_cli_parse.py
- tests/system/test_cli_render_golden.py
- tests/system/test_cli_scale.py
- tests/system/test_cli_sys_export.py
- tests/system/test_cli_sys_plan.py
- tests/system/test_cli_vet.py
- tests/system/test_cli_xref.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: '1. Each candidate file audited: does the CLI subcommand it exercises'
  evidence: []
- text: actually require project-root resolution via git? If yes and the
  evidence: []
- text: fixture never git-inits, apply the same fix as T-2943 (git-init +
  evidence: []
- text: commit via the shared conftest helpers).
  evidence: []
- text: 2. A real macOS CI run (post T-2943's land) re-measured to confirm
  evidence: []
- text: whether the fixed cluster shrank the 156-failure macOS baseline as
  evidence: []
- text: expected, and to check whether any of the candidate files above
  evidence: []
- text: still fail there specifically (a genuine macOS-only remainder, if
  evidence: []
- text: any exists after this pass).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2943 (macOS git returncode=128 cluster). The
concrete confirmed root cause for tests/system/test_cli_cycle.py (9 of
its 12 tests): the fixture writes files to tmp_path but never git-inits
it, so a `frob cycle <tmp_path>` invocation cannot resolve a project
root (T-2588's contract) and git's own `rev-parse --show-toplevel`
correctly exits 128 ("fatal: not a git repository") -- REPRODUCED
IDENTICALLY ON LINUX, right now, on current main, in a natives-built
worktree; this is NOT a macOS-specific defect and the leading
safe.directory hypothesis in T-2943's original body is KILLED (real git
stderr text captured: "fatal: not a git repository (or any of the
parent directories): .git", not a dubious-ownership message).

grep across tests/system/test_cli_*.py for calls to the shared
`git_init_and_config` helper (tests/system/conftest.py) turned up
several other files with ZERO calls despite exercising CLI subcommands
that may also require a resolvable project root: test_cli_arch.py,
test_cli_dup.py, test_cli_exports.py, test_cli_map.py,
test_cli_outline.py, test_cli_parse.py, test_cli_render_golden.py,
test_cli_scale.py, test_cli_sys_export.py, test_cli_sys_plan.py,
test_cli_vet.py, test_cli_xref.py. NOT individually verified here
(each command's actual root-resolution requirement needs checking --
not every one necessarily calls the same
`_resolve_project_root`/`gitio.repo_root` path `cycle` does, so this is
a candidate list, not a confirmed failure list).

Locally-sampled failures in tests/test_gates.py and
tests/test_ticket_leases.py on this same run showed UNRELATED failure
signatures (DOC004 CRLF/line-ending noise, a `--reason` CLI validation
SystemExit) -- neither matches the git-returncode=128 pattern, so they
are likely a different pre-existing/local-environment issue, not part
of this cluster. Worth a real macOS-runner comparison before assuming
they belong here at all.
