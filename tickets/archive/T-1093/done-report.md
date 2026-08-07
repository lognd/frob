## Done report

Wires frob.app._daemon_proxy (spawn/version-skew-self-heal/FROB_NO_DAEMON=1
bypass over the T-1092 socket daemon) into the CLI dispatch layer, and
proxies frob perf hot --json through it as the first fully-wired, proven
command. ensure_daemon() spawns the daemon (sys.executable subprocess of
run_socket_daemon) if no sidecar .frob/daemon.meta.json is recorded, and
SIGTERMs+respawns it on a version mismatch between that meta file and the
current client's installed frob version (self-healing skew, since
_socketd's protocol itself carries no version field and src/frob/serve/**
is a sibling ticket's scope this wave -- disclosed in
docs/modules/serve.md and filed as T-1105). query() honors
FROB_NO_DAEMON=1 as an unconditional bypass before any daemon I/O, and
maps every failure mode (Unreachable, RemoteError, Disabled) to a
transparent in-process fallback with no surfaced error and no hang.

frob perf hot --json's payload was split out into _hot_json/_hot_json_payload
so the daemon-hit and in-process branches share the exact same dict shape;
tests/test_app_daemon_proxy.py::TestDifferentialParity runs a real
subprocess-vs-subprocess (FROB_NO_DAEMON=1 in-process vs a live
run_socket_daemon-served) diff of the rendered JSON payload, proving
byte-for-byte parity -- the epic's #1 safety invariant.

Wiring the remaining query-shaped commands T-0321's integration map names
(outline/map/xref/parse/graph/exports/bind/docs/stats) is disclosed as a
scope cut in docs/modules/serve.md and filed as T-1106: most of
_socketd._TOOL_DISPATCH's other methods do not yet produce a
field-for-field-identical CLI JSON payload to diff against (e.g.
frob_graph_query's dict omits span/digests frob graph query --json
prints), and src/frob/app/ticket_runner.py / src/frob/tickets/** were
off-limits this wave (a sibling ticket's split), so frob ticket doable
specifically cannot be wired from this ticket's own scope.

### Changed
```
 docs/modules/serve.md          |  100 ++
 src/frob/app/_daemon_proxy.py  |  278 +++++
 src/frob/app/perf_runner.py    |   78 +-
 tests/test_app_daemon_proxy.py |  211 ++++
 tickets-archive.md             | 2532 +++++++++++++++++++++++++++++++++++++-
 tickets.md                     | 2640 ++--------------------------------------
 6 files changed, 3278 insertions(+), 2561 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_env_bypass` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_no_socket_falls_back` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestQuery::test_live_daemon_hit` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_perf_hot_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 1 error(s), 837 warning(s), 427 waived
- error-findings: TICK006@tickets.md
