---
id: T-1377
title: 'Genuine daemon liveness probe: classify Live/NoSocket/Orphaned/Wedged instead
  of collapsing to None'
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
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_probe_of_a_silent_listener_stays_within_budget
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_orphaned_socket_is_unlinked
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_missing_socket_is_nosocket
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_different_version_is_skew_not_live
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
designated_repro_test: null
acceptance:
- text: GIVEN a socket file whose daemon is gone WHEN the proxy probes THEN it classifies
    Orphaned, unlinks the socket, and spawns -- in well under a second
  evidence:
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_probe_of_a_silent_listener_stays_within_budget
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_orphaned_socket_is_unlinked
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_missing_socket_is_nosocket
  - tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_different_version_is_skew_not_live
- text: GIVEN a daemon that is alive but not answering WHEN the proxy probes THEN
    it classifies Wedged and does NOT spawn a competing daemon
  evidence:
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
- text: GIVEN any unhealthy daemon state WHEN frob check runs THEN the liveness probe
    costs at most the probe budget, not send_request's 10s query timeout
  evidence:
  - tests/test_app_daemon_proxy.py::TestProbeDaemon::test_probe_of_a_silent_listener_stays_within_budget
threat: null
component: null
---
Measured 2026-08-01. frob check --only gates --delta --json (the ONE shape _try_check_delta_via_daemon proxies) took 106s and then 198s against a daemon in a bad state, versus ~35s for the plain in-process path. The daemon is a net negative whenever it is not perfectly healthy.

Root cause is _query_daemon_version: it calls send_request(root, 'frob_version') with the DEFAULT timeout_s=10.0 -- a liveness probe budgeted like a real query -- and then collapses every distinct failure (no socket, connect refused, wedged process, malformed reply) to a single None meaning 'spawn a replacement'. So an unhealthy daemon costs up to 10s per invocation, plus a spawn, plus a _SPAWN_GRACE_S retry, on EVERY frob command that proxies.

Three states need distinguishing, each with a different correct action:
- NoSocket: no socket file. Spawn.
- Orphaned: socket file present but connect() is refused -- the file outlived its process. Unlink it, then spawn. Today this silently accumulates.
- Wedged: connect() succeeds but no valid reply within budget. A process IS alive holding the socket. Spawning a second one is exactly wrong (the singleton lock refuses it, so every invocation retries forever). Bypass in-process instead.

Also observed and in scope for a follow-up: the daemon leaks its multiprocessing forkserver and resource_tracker children on shutdown (four were left orphaned after SIGTERM), and a daemon whose socket file is deleted underneath it keeps running while being permanently unreachable -- it should notice its listening inode is gone and exit.

Probe budget should be sub-second: this is a local unix-socket round trip, so 0.5s is already ~1000x headroom.