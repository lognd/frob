---
id: T-3615
title: 'guard hooks: pass --help/--version and read-only verbs, never lexically match
  command content'
state: done
kind: ux
origin: human
created: '2026-08-31'
priority: medium
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks
- tests/unit/test_hooks_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks
  reason: hook fixes live in the repo copies of the hooks
  actor: logan
  at: '2026-09-15'
- op: add
  glob: tests/unit/test_hooks_guard.py
  reason: hook fixes live in the repo copies of the hooks
  actor: logan
  at: '2026-09-15'
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'T-4483 follow-up: TICK004 escalated to error on 2026-09-15 (15d queued
    > 2x the 7d high threshold) and reds every CI leg; these are T-3611 latency-epic
    children, sprint v0.532.0 work behind the v0.531.0 alpha cut, not alpha-path work,
    so medium is the honest priority'
  actor: logan
  at: '2026-09-14'
evidence:
- tests/test_hook_root_write_guard.py::test_bash_land_help_from_root_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_land_version_from_root_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_real_land_from_root_still_refused_alongside_help_fix
- tests/test_hook_root_write_guard.py::test_bash_compound_mkdir_touch_then_help_land_is_allowed
- tests/test_hook_root_write_guard.py::test_bash_compound_mkdir_touch_then_real_land_still_refused
- tests/test_hook_frob_timeout_guard.py::test_setsid_nohup_detached_land_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_naked_backgrounded_land_still_blocks
- tests/test_hook_frob_timeout_guard.py::test_backgrounded_check_still_blocks_despite_detach_exemption
- tests/test_hook_frob_timeout_guard.py::test_detached_land_with_sufficient_timeout_still_passes
- tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_when_import_is_only_elsewhere_in_line
- tests/test_hook_frob_suggest.py::test_hand_rename_sed_still_fires_when_import_is_in_the_script_itself
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three measured guard false-positives (see epic body): the root-write
guard and the frob-timeout-guard hooks match verb SHAPES and command
CONTENT lexically. Fix in the hooks (.claude/hooks/*, edit the REPO
copies, sync after): (a) any invocation whose argv contains
--help/--version, or whose verb is a documented read-only verb, passes
unconditionally regardless of cwd; (b) never scan heredoc/quoted string
CONTENT for verb phrases -- tokenize the actual command position
(shlex), fleet doctrine: token/grammar fixes, never lexical; (c) the
timeout-guard exempts --help/--version forms. Tests in the hook suites
for each: help-from-root passes, real land from root still refused,
heredoc containing verb phrases writing OUTSIDE the repo passes.