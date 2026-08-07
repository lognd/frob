## Done report

Replaced T-1093's client-written `.frob/daemon.meta.json` sidecar-file
version-skew check with a real protocol-level handshake on the socket
daemon itself.

`src/frob/serve/_socketd.py`: added `daemon_version()` (the daemon
process's own installed `frob` version) and two new JSON-RPC methods
special-cased in `_RequestHandler.handle` alongside `subscribe`:
`frob_version` (answers `{"version": ...}`) and `frob_shutdown` (starts a
helper thread that calls `server.shutdown()` and acknowledges
immediately -- calling `shutdown()` inline on the connection thread would
deadlock it against the very `serve_forever()` loop it is stopping).

`src/frob/app/_daemon_proxy.py`: `ensure_daemon` now calls
`_query_daemon_version` (a `send_request(root, "frob_version")`) instead
of reading a sidecar meta file; on a version mismatch it calls
`_shutdown_stale_daemon` (a `frob_shutdown` RPC, waiting on the lock file
to clear) instead of `SIGTERM`-by-recorded-pid. Removed `_meta_path`/
`_read_meta`/`_write_meta`/`_kill_stale_daemon` and the `.frob/
daemon.meta.json` sidecar entirely -- nothing writes it anymore.

Tests: added `TestDispatchRequest.test_frob_version_reports_daemon_version`
and `.test_frob_shutdown_stops_the_server` to tests/test_serve_socket.py
(real running daemon, real socket) -- required extending T-1105's scope
to include this test file (`frob ticket scope T-1105 --add
tests/test_serve_socket.py`), since the new RPC methods live in
_socketd.py and need direct socket-level coverage. Updated
tests/test_app_daemon_proxy.py's TestEnsureDaemon tests to mock the new
_query_daemon_version/_shutdown_stale_daemon seam instead of the removed
meta-file functions, and added a real end-to-end
test_version_handshake_end_to_end against a live daemon.

docs/modules/serve.md: added a new "Version handshake (T-1105)" section
under the socket-daemon docs describing the two new RPC methods, and
rewrote the "Version-skew self-heal" subsection under "CLI daemon proxy
(T-1093)" plus its decision-tree diagram to describe the RPC-based flow
instead of the sidecar file.

Cut: none -- T-1093's disclosed residual (a real version-handshake RPC,
tracked as T-1105 after its draft died at land) is now fully closed by
this ticket.

### Changed
```
 docs/modules/serve.md          |  79 +++++++++++++++------
 src/frob/app/_daemon_proxy.py  | 154 +++++++++++++++++++----------------------
 src/frob/serve/_socketd.py     |  55 +++++++++++++++
 tests/test_app_daemon_proxy.py |  49 ++++++++-----
 tests/test_serve_socket.py     |  45 ++++++++++++
 5 files changed, 259 insertions(+), 123 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestDispatchRequest::test_frob_version_reports_daemon_version` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestDispatchRequest::test_frob_shutdown_stops_the_server` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_version_handshake_end_to_end` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
