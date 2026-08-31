---
id: T-3570
title: 'macOS: frob vet --hook mode leaks a WARNING (sysctl failure) to stderr; must
  emit nothing'
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app
- src/frob/tickets/_land_finish_guard.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_worktree_guard.py
- src/frob/mutate/_journal.py
- tests/system/test_cli_vet.py
- src/frob/logging/logger.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/logging/logger.py
  reason: the general hook-mode WARNING suppression belongs at the logging init layer
    (mirrors T-3438's own sys.argv-scan pattern), not in the app/vet-hook-entry files
    alone
  actor: logan
  at: '2026-08-31'
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver
  actor: logan
  at: '2026-08-31'
  old_length: 642
  new_length: 1266
evidence:
- tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33370059331 (macOS): tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero requires hook mode to emit NOTHING, but stderr now carries a 'WARNING: pro...ctl failure' line -- a sysctl-failure warning from the T-3500 macOS ps/lsof live-process branch leaking into frob vet --hook. Fix at the right layer: (1) hook mode should suppress WARNING-and-below logging to stderr the same way T-3438 suppressed startup nags -- find that suppression and extend it to this path; (2) the T-3500 macOS branch should not WARN on an expected-per-call sysctl miss -- downgrade to DEBUG if it is routine, not a genuine failure.

frob:waive BUG002 reason="macOS-only defect (run 33370059331): the leaking WARNING is a macOS-only forkserver-pdeathsig-arm-failure log line (PR_SET_PDEATHSIG has no equivalent on darwin, T-2944), which never fires on this Linux dev box, so the pre-fix state already passed here and cannot fail-then-pass. The fix (suppressing the stderr handler above WARNING in vet --hook mode, in src/frob/logging/logger.py) is a general, platform-independent logging-layer fix verified locally: 3x pass on the touched test plus a full tests/system/test_cli_vet.py + tests/unit/test_main_entry.py regression run (43 tests, 0 failures)."