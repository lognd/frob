---
id: T-0474
title: 'frob ticket start is not instant: it runs a synchronous whole-repo dup+xref
  pre-work sweep (57s on /mnt/c) instead of just the queued->in-progress transition
  -- defer/background/incrementalize the baseline snapshot'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/tickets.md
- tests/unit/test_app_runners_batch7.py
- tests/system/test_cli_ticket_worktree_root.py
- tests/test_prework_parity.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-0474: instant start -- background the pre-work sweep, --foreground opts
    back in'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'T-0474: instant start -- background the pre-work sweep, --foreground opts
    back in'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/system/test_cli_ticket_worktree_root.py
  reason: 'T-0474: instant start -- background the pre-work sweep, --foreground opts
    back in'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_prework_parity.py
  reason: 'T-0474: instant start -- background the pre-work sweep, --foreground opts
    back in'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets.md
  reason: 'T-0474: instant start -- background the pre-work sweep, --foreground opts
    back in'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep
- tests/system/test_cli_ticket_worktree_root.py::TestTicketRootFromLinkedWorktree::test_ticket_start_prework_written_under_worktree
- tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean
designated_repro_test: null
threat: null
component: null
---
