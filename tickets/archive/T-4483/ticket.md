---
id: T-4483
title: 'main red after T-4480: DRIFT001 run_diagnosis ack, REF002 macos-portability
  single anchor, win32 agent env quoted PYTHONPATH assertion'
state: done
kind: bug
origin: agent
created: '2026-09-14'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_worktree_pythonpath.py
- docs/design/windows-portability.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4483: BUG002 refused the land because the win32-only repro passes on
    the Linux land host; record the platform boundary as a waiver'
  actor: logan
  at: '2026-09-14'
  old_length: 1492
  new_length: 1937
evidence:
- tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_env_output_names_worktree_src_on_pythonpath
designated_repro_test: null
threat: null
component: ci
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

CI run 34836067875 on main (d676c3b49) is red on every leg. The self-gate
(identical on ubuntu, macOS and Windows) reports exactly two errors, and the
Windows Test step has exactly one failing test:

1. DRIFT001 at src/frob/doctor.py::run_diagnosis (body facet): the digest
   moved when T-4459 added the import_source computation and threaded it
   through report assembly. The contract the acked doc describes is
   unchanged and the new field is documented in
   docs/modules/agent-worktree.md, so the fix is a re-verified ack.
2. REF002 at docs/design/macos-portability.md: exactly one inbound
   reference (docs/index.md). docs/design/windows-portability.md already
   argues from macos-latest health without naming its sibling design doc;
   pointing it there is the natural second consumer.
3. tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_env_output_names_worktree_src_on_pythonpath
   fails on windows-latest only: frob agent env renders every value through
   shlex.quote, and a Windows path containing backslashes is single-quoted,
   so the raw-substring assertion never matches. POSIX paths need no quoting,
   which is why the test passed there. The assertion must compare against
   the quoted form the emitter actually prints.

## Acceptance

- frob check self-gate reports 0 errors on main.
- The named test passes on windows-latest (measured by the CI run that
  lands this ticket; the quoted form is asserted on every platform).

## Reproduction boundary

frob:waive BUG002 reason="the defect is win32-only: shlex.quote leaves a POSIX path bare, so the bound test PASSES at main on Linux and macOS and only fails on windows-latest (CI run 34836067875, job 103950053791); the Linux land host cannot fail it at the parent commit, and the other two findings are a doc anchor and an ack, which have no test at all -- the Windows CI leg of the landing push is the reproduction"