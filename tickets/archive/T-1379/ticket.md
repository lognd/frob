---
id: T-1379
title: Make the check daemon opt-in until its shutdown/leak/CPU defects are fixed
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/_daemon_proxy.py
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_unset_env_disables_the_daemon
- tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_frob_daemon_1_enables_the_daemon
- tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_no_daemon_still_wins_over_opt_in
designated_repro_test: null
acceptance:
- text: GIVEN no daemon environment variable is set WHEN a proxying frob command runs
    THEN it computes in-process and never spawns a daemon
  evidence:
  - tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_unset_env_disables_the_daemon
- text: GIVEN FROB_DAEMON=1 is set WHEN a proxying frob command runs THEN the daemon
    path is used exactly as before
  evidence:
  - tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_frob_daemon_1_enables_the_daemon
threat: null
component: null
---
T-1378 documents three unfixed daemon defects: frob_shutdown is acknowledged but ignored (needed SIGKILL), the multiprocessing forkserver/resource_tracker children leak on exit, and the daemon's pool competes with the foreground check for CPU badly enough to be a pessimization on a 4-core WSL box (load 0.4 idle -> 5-8 during a single check, with repeated runs getting SLOWER rather than warming).

Today the daemon is opt-OUT: it auto-spawns unless FROB_NO_DAEMON=1. That means any unsuspecting session pays those defects by default. T-1377 removed the pathological stalls but explicitly did not make the daemon a win.

Flip the default to opt-IN (FROB_DAEMON=1) until T-1378 lands. FROB_NO_DAEMON=1 keeps working as an explicit bypass so existing scripts and the differential test are unaffected.