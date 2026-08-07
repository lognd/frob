## Done report

The proxy treated "socket file exists" plus a 10-second RPC as its health
check, then collapsed every distinct failure onto `None`, meaning "spawn a
replacement". That is the correct response to exactly one of the four
states it can actually be in.

Concretely, an unhealthy daemon cost every proxying `frob` invocation up
to 10s (`send_request`'s default query timeout, used verbatim for a
liveness probe) plus a spawn plus a `_SPAWN_GRACE_S` retry. Measured on
this repo, `frob check --only gates --delta --json` -- the one shape the
proxy serves -- took 106s and then 198s against a daemon in a bad state,
versus ~35s for the plain in-process path.

`probe_daemon` now classifies, in a 0.5s budget:

- `NoSocket`   -> spawn.
- `Orphaned`   -> the socket file outlived its process (connect refused).
                  Unlink it, then spawn. Previously these accumulated and
                  every future probe paid another refused connect.
- `Wedged`     -> something IS listening but did not answer. Spawning a
                  rival is the actively harmful case: the singleton lock
                  refuses it, so every later invocation pays another
                  failed spawn. Now it bypasses in-process instead.
- `VersionSkew`-> unchanged shutdown-and-respawn path.
- `Live`       -> use it.

Unclassifiable failures report `Wedged` deliberately: it is the state
where doing nothing is safest.

I found this the hard way and the mistake is worth recording. Diagnosing a
slow run, I checked `pgrep socketd`, saw nothing, concluded the socket was
stale, and deleted it -- out from under a LIVE daemon whose process is
named `run_socket_daemon`. Process-name matching and socket-file existence
are both unreliable liveness signals; only a real round trip is evidence.
That is exactly what this ticket replaces them with.

NOT fixed here, filed as T-1378: the daemon ignores a `frob_shutdown` it
acknowledged (still alive 20s later, needed SIGKILL), leaks its
multiprocessing forkserver/resource_tracker children, and competes with
the foreground check for CPU badly enough that it is a pessimization on
this machine. This ticket removes the pathological stalls; it does not
make the daemon a win. `FROB_NO_DAEMON=1` remains the right setting for
interactive work until T-1378 lands.

### Changed
(no changed files detected)

### Evidence
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_probe_of_a_silent_listener_stays_within_budget` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_orphaned_socket_is_unlinked` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_missing_socket_is_nosocket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
