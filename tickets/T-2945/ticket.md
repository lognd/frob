---
id: T-2945
title: 'AF_UNIX socket path too long on macOS: relocate daemon.sock off deep project-root
  paths'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_socketd.py
- src/frob/app/_daemon_proxy.py
- docs/modules/serve.md
- tests/test_serve_socket.py
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/serve/_socketd.py;src/frob/app/_daemon_proxy.py;docs/modules/serve.md;tests/test_serve_socket.py;tests/test_app_daemon_proxy.py
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/serve.md
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_serve_socket.py
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'T-2945: fix a malformed single-glob scope entry (semicolon-joined instead
    of five separate globs) filed by mistake in T-2930''s triage'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_serve_socket.py::TestSocketPath::test_short_regardless_of_root_depth
- tests/test_serve_socket.py::TestSocketPath::test_normal_depth_root_still_works
- tests/test_serve_socket.py::TestSocketPath::test_stable_for_the_same_root
- tests/test_serve_socket.py::TestSocketPath::test_distinct_roots_get_distinct_paths
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on the real macOS runner (T-2917 PR#1 run 32920399634, job
98032723003): 28 of 156 macOS pytest failures are in daemon/socket
tests (tests/test_app_daemon_proxy.py x20, tests/test_serve_socket.py,
tests/test_serve_events.py, tests/test_serve_daemon.py,
tests/test_daemon_proxy_lease_t1276.py, tests/test_coverage_wait_shared.py),
all failing with `OSError: AF_UNIX path too long` or a downstream
"daemon never became reachable" timeout.

ROOT CAUSE (verified in log): `src/frob/serve/_socketd.py::socket_path`
builds the unix-domain socket path as `<project root>/.frob/daemon.sock`
(`_SOCKET_REL`). macOS's `sockaddr_un.sun_path` is only 104 bytes
(vs Linux's 108), and macOS temp/test paths are structurally much
deeper than Linux's (`/private/var/folders/<hash>/<hash>/T/pytest-of-
runner/pytest-0/popen-gwN/<test-name>/.frob/daemon.sock` routinely
exceeds 104 bytes even for a short test name). This is a REAL
portability defect, not test-only fragility: any project checked out
to a sufficiently deep path on macOS (not just CI tmpdirs -- a deeply
nested Homebrew Cellar path, an iCloud Drive sync folder, a long
username, etc.) will hit the identical `AF_UNIX path too long` in
production, silently breaking the socket-daemon fast path (`frob
serve`'s standalone daemon frontend, T-1092) while `frob` itself
still works via the cold-graph-rebuild fallback -- so this degrades
performance invisibly rather than crashing outright, which is worse to
diagnose.

FIX SHAPE (not designed here -- this ticket is to design and implement
it): relocate the actual socket file to a short, collision-safe path
outside the project root -- e.g. a system temp directory keyed by a
hash of the resolved project root (`$TMPDIR/frob-<hash>.sock` or
`/var/run/frob/<hash>.sock` root-permission issues aside), while
keeping `.frob/daemon.lock` (or a new pointer file) at the existing
per-root location so `lock_path`/discovery semantics do not change.
Must preserve: exactly one daemon per project root (the existing
flock-based singleton guard must still key correctly), and callers
resolving "the socket for this root" must still work from a stale/
relocated project checkout. `socket_path` and its docstring
(`docs/modules/serve.md#socket-daemon-t-1092`) are the public surface
to update; `_daemon_proxy.py`'s own socket-open call sites are the
other half.

Do NOT special-case macOS-only: the identical AF_UNIX length limit
exists on Linux too (108 bytes), just less likely to be hit given
Linux's flatter tmp/test paths -- the real fix is platform-independent
(a short path everywhere), not a `sys.platform` branch.