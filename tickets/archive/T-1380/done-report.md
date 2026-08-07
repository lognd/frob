## Done report

T-1377 and T-1379 closed before their own gate obligations were fully
discharged. This ticket carries the remainder rather than leaving the
closed tickets half-accounted:

- `probe_daemon` split into `_ask_version_over_socket` (bounded transport)
  and `_classify_version_reply` (interpretation), clearing ARCH103 on the
  original combined body. The remaining ARCH103 on the transport half is
  waived with reason: a socket health probe IS connect-send-recv plus the
  two failure decisions those calls produce, and the classification half
  is already extracted.
- `frob:doc` edges added for `DaemonLiveness`, `probe_daemon` and
  `_daemon_enabled`, pointing at a new docs/modules/serve.md section that
  documents the five liveness states, why the probe budget is deliberately
  NOT `send_request`'s 10s query timeout, and why `Wedged` must not spawn.
- `frob:tests` directives corrected from `::Class::method` to the
  `::Class.method` target form the gate actually resolves (DOC007/DRIFT002).
- `design/frob.strata` synced for the seven new public test classes
  (SELFAUDIT001/SYS104).
- REL001: minor bump to 0.294.0, then stamped. I first stamped WITHOUT
  bumping, which silently absorbs an API change into the old version --
  reverted and redone in the right order. That footgun is now its own
  ticket, since `frob release stamp` should refuse it rather than rely on
  me noticing.

### Changed
(no changed files detected)

### Evidence
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 1802 warning(s), 697 waived
- error-findings: E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215
