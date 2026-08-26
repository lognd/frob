---
id: T-2967
title: 'macOS: frob.serve._socketd daemon.sock exceeds AF_UNIX sun_path length limit
  (12 failures)'
state: queued
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
no_scope_declared: false
no_scope_declared_reason: null
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
land_commit: null
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
