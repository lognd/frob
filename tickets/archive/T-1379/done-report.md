## Done report

T-1377 made the daemon's liveness probe honest and bounded, but it did not
make the daemon a net win, and T-1378 records three defects that are still
open: `frob_shutdown` is acknowledged and then ignored (the process needed
SIGKILL), the multiprocessing forkserver/resource_tracker children leak on
exit, and the daemon's pool competes with the foreground check for CPU
badly enough to be a pessimization here (idle load 0.4 -> 5-8 during a
single check, with repeated proxied runs getting SLOWER, not warmer).

The daemon was opt-OUT, so every session paid for those defects by default
without knowing the feature existed. Flipped to opt-IN via `FROB_DAEMON=1`.
`FROB_NO_DAEMON=1` still wins outright, so existing scripts and the
differential-parity test are unaffected.

This is a safety default, not a fix. Revert it to opt-out once T-1378
lands and the daemon demonstrably beats the in-process path.

### Changed
(no changed files detected)

### Evidence
- `tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_unset_env_disables_the_daemon` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_frob_daemon_1_enables_the_daemon` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDaemonOptIn::test_no_daemon_still_wins_over_opt_in` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 1603 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/app/_daemon_proxy.py, ARCH103@src/frob/app/_daemon_proxy.py, COV001@src/frob/app/_daemon_proxy.py, COV005@src/frob/app/_daemon_proxy.py, DOC007@src/frob/app/_daemon_proxy.py, DRIFT002@src/frob/app/_daemon_proxy.py, E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1379, SELFAUDIT001@design
