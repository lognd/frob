---
id: T-3311
title: Collapse the three divergent external-tool spawn conventions into one resolution
  helper
state: done
kind: feature
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/refactor/_verify.py
- src/frob/perf/_profile.py
- src/frob/process/_pytest_spawn.py
- src/frob/process/__init__.py
- docs/modules/process.md
- tests/unit/test_pytest_spawn.py
- docs/commands/refactor.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_pytest_spawn.py
  reason: shared pytest-spawn resolution helper's natural home, importable without
    inverting gates/refactor/app layering
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/process/__init__.py
  reason: shared pytest-spawn resolution helper's natural home, importable without
    inverting gates/refactor/app layering
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/process.md
  reason: T-3311's new resolve_pytest_argv/pytest_importable public API needs its
    frob:describes anchor
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: docs/modules/process.md
  reason: T-3295 needs this file's lease to land first (coordinator sequencing); will
    re-add and merge when T-3311 resumes
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/process.md
  reason: re-add after rebase onto main dropped these from the worktree-local ticket
    ledger
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_pytest_spawn.py
  reason: re-add after rebase onto main dropped these from the worktree-local ticket
    ledger
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/process.md
  reason: 'resume T-3311: re-add process.md now that T-3295 has landed, per the pause
    note'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/commands/refactor.md
  reason: 'AFFECT001: verify_pytest_collect''s argv-build now routes through resolve_pytest_argv,
    doc needs updating'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: the ARCH001 split moved an existing (undeclared) exec call
    site onto a fresh line; declaring it properly rather than waiving'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_pytest_spawn.py::TestPytestImportable::test_true_when_importable
- tests/unit/test_pytest_spawn.py::TestPytestImportable::test_false_when_not_importable
- tests/unit/test_pytest_spawn.py::TestResolvePytestArgv::test_ok_uses_sys_executable
- tests/unit/test_pytest_spawn.py::TestResolvePytestArgv::test_appends_extra_args
- tests/unit/test_pytest_spawn.py::TestResolvePytestArgv::test_err_when_not_importable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3276 built the doctor.py inventory/preflight side (ToolCategory, ExternalToolStatus, scan_external_tools, _EXTERNAL_TOOLS) but its declared scope was doctor.py only. The three divergent spawn conventions T-3276 measured are still live: sys.executable -m pytest (gates/_bug_repro.py, CORRECT), uv run pytest (app/ticket_runner/_verify.py), bare pytest --collect-only (refactor/_verify.py), and bare python (perf/_profile.py, T-3268's own fix target). Collapse these into one resolution helper (frob._EXTERNAL_TOOLS-aware, sys.executable-based per T-3268's adopted convention) that every spawn site calls, with a loud typed Result error on a REQUIRED tool's absence. Coordinate with T-3268 if still open.