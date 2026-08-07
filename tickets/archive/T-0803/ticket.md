---
id: T-0803
title: wire remaining subprocess call sites through the T-0200/T-0778 exec guard (tickets
  git spawn, gitlog, fleet, clipboard, mutate, deploy, scaffold, coverage-wait)
state: done
kind: security
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/gitlog/__init__.py
- src/frob/app/ticket_runner.py
- src/frob/fleet/__init__.py
- src/frob/tickets/clipboard.py
- src/frob/mutate/__init__.py
- src/frob/deploy/_vm_runner.py
- src/frob/scaffold/project.py
- src/frob/testing/_coverage_wait.py
- src/frob/app/gitlog_runner.py
- tests/test_app.py
- tests/test_clipboard.py
- tests/test_mutate.py
- tests/test_tickets_lease.py
- tests/unit/deploy/test_vm_runner.py
- tests/unit/fleet/test_status.py
- tests/unit/test_gitlog.py
- tests/unit/test_scaffold_project.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/gitlog_runner.py
  reason: T-0778's guarded_subprocess_run adds a DEBUG spawn log; gitlog's --json
    runner needed quiet_stdout_logs wrapping to avoid leaking it into stdout output
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_app.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_clipboard.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_mutate.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_lease.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/deploy/test_vm_runner.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/fleet/test_status.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_gitlog.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: kill-switch test for T-0803's guarded_subprocess_run wiring
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_gitlog.py::test_git_log_kill_switch_refuses_without_spawning
- tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning
- tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_kill_switch_refuses_without_spawning
- tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_kill_switch_refuses_without_spawning
- tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_kill_switch_refuses_without_spawning
- tests/test_clipboard.py::TestKillSwitch::test_clipboard_image_kill_switch_refuses_without_spawning
- tests/test_mutate.py::test_run_mutations_kill_switch_refuses_without_spawning
- tests/unit/deploy/test_vm_runner.py::TestAvail::test_kill_switch_refuses_without_spawning
- tests/unit/test_scaffold_project.py::test_hooks_dir_kill_switch_refuses_without_spawning
- tests/test_app.py::TestRunCoverageWait::test_kill_switch_refuses_without_spawning
designated_repro_test: null
threat: null
component: null
---
T-0778 (H2 fix) wired frob.gitio.run_argv through
frob.process._guard.guarded_subprocess_run, which transitively covers every
git spawn that already goes through gitio (serve daemon, gitio-based lease
reads). The T-0778 sweep (grep subprocess.run/Popen/call/check_output
outside src/frob/process/_guard.py and src/frob/gitio.py) found additional
call sites that still bypass the guard entirely -- FROB_DISABLE_EXEC=1 does
NOT stop these:

- src/frob/tickets/__init__.py:930 `_repo_files_git` -- direct `git
  ls-files` subprocess.run, not routed through gitio.run_argv. This is a
  real git spawn the audit's "tickets lease" language pointed at.
- src/frob/tickets/__init__.py:2370 `_run_evidence_command` -- shell=True
  evidence-command spawn (caller-supplied command, T-0215); arguably
  intentionally outside a git-argv guard shape, but still an unguarded
  exec capability.
- src/frob/gitlog/__init__.py:230 -- direct `git log` subprocess.run.
- src/frob/app/ticket_runner.py:863,1159 -- subprocess.run/Popen.
- src/frob/fleet/__init__.py:164,194 -- subprocess.run.
- src/frob/tickets/clipboard.py (9 call sites) -- subprocess.run for
  clipboard tool spawns (pbcopy/xclip/etc).
- src/frob/mutate/__init__.py:260 -- subprocess.run.
- src/frob/deploy/_vm_runner.py:109,116,134,153 -- subprocess.run.
- src/frob/scaffold/project.py:509 -- subprocess.run.
- src/frob/testing/_coverage_wait.py:151 -- subprocess.run (noqa S603).

Fix: for each site, either route it through
frob.process._guard.guarded_subprocess_run (preferred, matching T-0778's
gitio wiring), or justify in a code comment why it must stay outside the
kill switch (e.g. a non-exec-capability tool, or a case where refusing to
spawn would be actively harmful) and record that justification in
design/frob.strata as a real `attr flag=` or an honest waiver -- never a
"T-0200 is pending" waiver again, since the mechanism is real now.
Prioritize the two GIT call sites (tickets/__init__.py:930,
gitlog/__init__.py:230) since those are the closest remaining gap to
FROB_DISABLE_EXEC's advertised "stops every process this component
spawns" claim.