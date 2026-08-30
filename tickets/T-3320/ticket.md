---
id: T-3320
title: 'Fresh ticket-work worktree has no venv: ty fails on every declared dep until
  manual uv sync'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_ticket_runner_venv_sync_t3320.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_venv_sync_t3320.py
  reason: unit test coverage for the venv-sync fix, no source outside declared scope
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_runs_uv_sync_in_the_worktree
- tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_exec_disabled_degrades_to_a_warning_not_sys_exit
- tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_nonzero_exit_degrades_to_a_warning_not_sys_exit
- tests/unit/test_ticket_runner_venv_sync_t3320.py::TestSyncVenvForWork::test_runs_before_natives_build_in_the_work_flow
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-017). A first-hour
blocker: this is what happens the FIRST time a new user runs `frob ticket
work` on a freshly scaffolded project.

A fresh worktree created by `frob ticket work T-0002` has no `.venv` of its
own. `frob check --ticket` run there then fails `ty` with "Cannot resolve
imported module" for pydantic/dotenv/pytest across 3 platforms (the
scaffold's own declared deps). Running `uv sync` in the worktree by hand
fixes it. `ticket work`'s own "warmup" hint mentions `frob agent env` but
does not actually run `uv sync` or say the venv is missing.

NOTE THE INTERACTION with the self-verification ticket filed alongside this
one (F-014's root cause): a worktree WITHOUT a venv currently gets the
correct `sys.executable` fallback in `_python_for_tree` today, so F-017's
"fix" (create a venv) and F-014's fix (verify frob is importable before
trusting a tree venv) must land compatibly -- confirm the F-014 fix handles
a freshly-`uv sync`'d worktree venv correctly (frob still won't be in it,
since frob is a global tool, not a project dep) before/alongside this one.

WHAT TO BUILD: either run `uv sync` as part of `ticket work`'s worktree
creation/warmup step, or -- if that is judged too slow/heavy to run
unconditionally -- have the warmup hint say explicitly "run `uv sync` in
this worktree before `frob check`" rather than pointing only at
`frob agent env`.

MUST-FIRE / MUST-STAY-QUIET: a fresh `frob ticket work <id>` worktree,
immediately followed by `frob check --ticket <id>` -- either it just works
(if uv sync is wired into warmup) or the warmup output explicitly names the
`uv sync` step needed first; no more silent 3-platform ty failures with no
explanation.
