---
id: T-1378
title: 'The check daemon is a net negative: it competes for CPU, ignores frob_shutdown,
  and leaks its forkserver pool'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_socketd.py
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve_socket.py
  reason: The ticket's own acceptance criteria require regression tests (frob_shutdown
    actually exits, no leaked multiprocessing child survives) and this repo's convention
    binds such evidence into the existing tests/test_serve_socket.py module; minimal
    widening, re-applied after the 10b ledger restore.
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
- tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
- tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
designated_repro_test: null
acceptance:
- text: GIVEN a frob_shutdown RPC that returns ok WHEN 5 seconds pass THEN the daemon
    process has actually exited
  evidence:
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
  - tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
- text: GIVEN a daemon that exits WHEN it is gone THEN no multiprocessing forkserver
    or resource_tracker child of it survives
  evidence:
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick
  - tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op
  - tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
acceptance_amendments:
- op: remove
  index: 2
  old_text: GIVEN a warm daemon WHEN frob check --only gates --delta --json runs THEN
    it is not slower than the same command with FROB_NO_DAEMON=1
  new_text: null
  reason: 'split to the follow-up ticket filed as T-draft-8e923fbc in this worktree:
    the forkserver-pool CPU contention root cause lives in src/frob/serve/_tools.py,
    outside this ticket''s declared scope (_socketd.py); criteria [0]/[1] are bound
    and delivered'
  actor: logan
  at: '2026-08-02'
threat: null
component: null
---
Measured 2026-08-01 alongside T-1377. Three separate defects, all observed directly:

1. frob_shutdown acknowledges but does not stop. send_request(root, 'frob_shutdown') returned Ok, and the daemon process was still alive 20+ seconds later; it took SIGTERM, then SIGKILL. So the graceful-stop path cannot establish that a daemon is genuinely GONE, which is the mirror of the liveness problem T-1377 fixes for genuinely ALIVE. _shutdown_stale_daemon's version-skew path trusts this RPC and only waits _SHUTDOWN_GRACE_S=1.0s for the lock, so on a real skew it will proceed to spawn while the old daemon is still up.

2. It leaks its multiprocessing children. After the daemon died, its forkserver and resource_tracker processes survived and had to be reaped by hand; repeated spawns accumulated several.

3. It costs more than it saves on this box. With a daemon up, load average went from ~0.4 idle to 5-8 while a single frob check ran, and the proxied shape got SLOWER across repeated runs rather than warming up. The daemon's forkserver pool competes with the foreground check for the same cores, so on a 4-core WSL machine the proxy is a pessimization.

Until this is fixed, FROB_NO_DAEMON=1 is the correct default for interactive work and the docs should say so. T-1377 removes the pathological stalls (10s probe, respawn storms) but does NOT make the daemon a win.