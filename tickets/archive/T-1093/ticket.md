---
id: T-1093
title: 'daemon: CLI auto-proxy to socket daemon with transparent in-process fallback'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
blocked_by:
- T-1092
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/app/**
- src/frob/__main__.py
- Makefile
- docs/modules/serve.md
- docs/modules/app.md
- tickets.md
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_env_bypass
- tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_no_socket_falls_back
- tests/test_app_daemon_proxy.py::TestQuery::test_live_daemon_hit
- tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_perf_hot_json_daemon_matches_in_process
designated_repro_test: null
acceptance:
- text: GIVEN a fresh clone with no daemon running WHEN a user runs frob check THEN
    it autostarts the daemon transparently (no init/deinit command issued) and the
    result is identical to the pre-existing in-process path
  evidence:
  - tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded
  - tests/test_app_daemon_proxy.py::TestQuery::test_live_daemon_hit
- text: GIVEN the daemon is unreachable, crashed, or reports a stale frob version
    WHEN a client issues any command THEN the client silently falls back to in-process
    computation with no surfaced daemon error and no hang, and best-effort respawns
    a fresh daemon
  evidence:
  - tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_no_socket_falls_back
  - tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back
  - tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
- text: GIVEN FROB_NO_DAEMON=1 is set WHEN any frob command runs THEN it fully bypasses
    the daemon and produces output identical to a daemon-served run (differential
    parity)
  evidence:
  - tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_env_bypass
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_perf_hot_json_daemon_matches_in_process
threat: null
component: null
---
Child (d) of T-0321. Today nothing in src/frob/app/ or __main__.py references 'daemon' at all (confirmed 2026-07-28) -- the CLI always computes in-process; T-1092's socket daemon exists but nothing talks to it. Wire the frob CLI entrypoint to: (1) probe for a live daemon socket for the current project root, (2) if present and version-matched, proxy the query-shaped subcommands (outline, map, xref, parse, graph, exports, bind, docs, stats, check-delta-style reads per T-0321's integration map) over the socket instead of recomputing, (3) on any failure (no socket, connect refused, stale version reported by the daemon, timeout) transparently fall back to the existing in-process code path with zero user-visible error, (4) respect FROB_NO_DAEMON=1 as an unconditional bypass. Makefile targets stay thin shims calling frob subcommands (no Makefile-level daemon awareness). Also implements T-0321's HARD requirement 6 (self-healing version skew): the client detects a version-mismatched daemon and triggers its self-replacement rather than erroring. Add a differential test asserting daemon-served and in-process answers are byte-identical for each proxied query type -- this is T-0321's #1 safety invariant (correctness must not depend on the daemon).