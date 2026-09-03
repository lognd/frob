---
id: T-2967
title: 'macOS: frob.serve._socketd daemon.sock exceeds AF_UNIX sun_path length limit
  (12 failures)'
state: dropped
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: decision-record ticket being dropped as confirmed duplicate;
  no code fix in this ticket
designated_repro_test: null
acceptance:
- text: 1. Root-cause confirmed by reading frob.serve._socketd's bind path
  evidence: []
- text: construction and the exact platform limit it exceeds.
  evidence: []
- text: 2. Either the socket path is shortened below every supported platform's
  evidence: []
- text: sun_path limit, or a bind failure due to AF_UNIX path length falls
  evidence: []
- text: back gracefully instead of raising/failing the caller.
  evidence: []
- text: 3. tests/test_app_daemon_proxy.py's 12 currently-failing (on macOS)
  evidence: []
- text: node ids pass on a macOS run, or on a local reproduction of a long
  evidence: []
- text: tmp path if a real macOS runner is unavailable.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 44175e80973c25dff10e4e602da801ed11de5ac2
---
Found while working T-2943 (macOS git returncode=128 cluster triage) --
this is a SEPARATE, larger failure cluster on the same macOS run
(32920399634, job 98032723003): 12 of the 156 macOS failures, all in
tests/test_app_daemon_proxy.py, share the real stderr text:

  ERROR frob.serve._socketd:_socketd.py:732 serve: socketd: bind failed
  at <long-macos-tmp-path>/.frob/daemon.sock: AF_UNIX path too long

This is a REAL portability defect, not test fragility: macOS's
sockaddr_un.sun_path limit is 104 bytes vs Linux's 108, and macOS's
system tmpdir (/private/var/folders/<hash>/T/pytest-of-.../popen-gwN/
<test-name>0/.frob/daemon.sock) is long enough to exceed it routinely --
especially under pytest-xdist's popen-gwN naming, which adds another
path segment. frob.serve._socketd binds its daemon socket at a path
derived from the project root without checking/handling this length
limit on macOS (or any platform).

NOT investigated as part of T-2943 (out of that ticket's
src/frob/gitio.py scope -- this is frob.serve._socketd, unrelated to
git subprocess handling): the fix likely needs either (a) binding the
daemon socket under a short, platform-provided tmp path (e.g. via
`tempfile.gettempdir()` rather than a path derived from the project
root) with a symlink/lookup from the project's own .frob/ directory, or
(b) falling back gracefully (skip the daemon fast path, same
correctness, no crash) when the resolved socket path exceeds the
platform's sun_path limit.

## Failure log
- 2026-08-26 attempt 1: dispatched as T-2967 by id mismatch; actual content is macOS AF_UNIX sun_path length limit, not the exit-code-contract mismatch task briefed (that is T-2968); no work done on this ticket's scope, returning to queue untouched
- 2026-08-28 attempt 2: stale premise: T-2945 (done) already fixed this exact defect

## Drop reason
- 2026-08-28: 2026-08-28 confirmed duplicate of T-2945 (done). T-2945's done report shows the exact same root cause (src/frob/serve/_socketd.py::socket_path building <root>/.frob/daemon.sock, exceeding macOS's 104-byte sockaddr_un.sun_path limit under deep pytest-xdist tmp paths) and the exact same fix (relocate to <system temp dir>/frob-<16-hex-digest-of-root>.sock, keep lock_path unchanged, updated docs/modules/serve.md). Verified directly in this worktree: src/frob/serve/_socketd.py already contains the T-2945 fix (short_socket_filename / hash-based relocation, docstring citing the 104/108-byte limit) and tests/test_serve_socket.py::TestSocketPath (4 tests) + tests/test_app_daemon_proxy.py TestProbeDaemon/TestProbeDaemonVersion pass locally, 9/9. T-2967's own failure-log attempt 2 already flagged this; this attempt re-confirms it with a fresh local test run rather than trusting the prior note.
