---
id: T-2963
title: 'Windows-native daemon transport (epic): named pipes vs loopback TCP+token
  vs AF_UNIX hybrid'
state: queued
kind: feature
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
- src/frob/serve/**
- src/frob/app/_daemon_proxy.py
- tests/test_app_daemon_proxy.py
- tests/test_serve_socket.py
- tests/test_serve_events.py
- tests/test_serve_leases.py
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
EPIC, not a single-session task. Filed per T-2961's own assessment
(approved by coordinator before T-2961's scoped fix landed) -- do NOT
attempt this as the tail of an already-long session; decompose before
starting.

CONTEXT: T-2961 made the daemon (frob.serve._socketd,
frob.app._daemon_proxy) refuse loudly and safely on Windows rather than
crashing at import time or failing ty check -- the daemon is a pure,
non-load-bearing warm-cache optimization (every caller already falls
back to in-process on any Err, per ProxyReason's own documented
contract and the differential-parity test suite), so a scoped refusal
was the correct interim answer. This epic is about whether Windows
should eventually get a REAL daemon transport, not about unblocking
anything urgent.

THE PROBLEM: the daemon's entire transport is a POSIX unix domain
socket (`.frob/daemon.sock`), both client (`socket.AF_UNIX`) and server
(`socketserver.ThreadingUnixStreamServer`). Windows has no drop-in
equivalent for the server half regardless of Python/OS version.

OPTIONS (from T-2961's assessment, not yet evaluated in depth):

1. AF_UNIX-on-Windows (client half only). Windows 10 1803+ supports
   AF_UNIX at the OS level, and CPython exposes `socket.AF_UNIX` on
   Windows since 3.9. This means the CLIENT side (connect/send/recv)
   may already work on modern Windows/Python combinations -- but
   `socketserver.ThreadingUnixStreamServer` (the SERVER half) has no
   cross-platform equivalent regardless: typeshed does not expose it
   for win32, and CPython's own socketserver module gates the Unix
   server classes independently of AF_UNIX's own availability. Even if
   this path is viable for the client, a real Windows daemon still
   needs a different SERVER implementation. This option alone does not
   close the gap -- named below for completeness, since a hybrid
   (AF_UNIX client talking to a differently-implemented server) is a
   real, if unusual, shape.

2. Windows named pipes (`\\.\pipe\...`). The idiomatic Windows local-
   IPC primitive, with real client/server support via `pywin32`
   (already a dependency of this repo's Windows extra, per
   pyproject.toml) or `asyncio`'s Proactor-based pipe support. Needs a
   SEPARATE code path from the unix-socket one (not a drop-in swap --
   different bind/connect/accept API shape entirely), which is real
   design and testing work: a second server implementation, a second
   client implementation, and re-verified parity with the existing
   differential-parity test suite (tests/test_app_daemon_proxy.py) for
   every proxied query shape.

3. Loopback TCP with a token. Cross-platform or Windows-specific,
   simplest to implement (stdlib `socketserver.ThreadingTCPServer` is
   NOT platform-gated), but changes the trust model: a unix socket
   under `.frob/` inherits filesystem permissions and is only reachable
   by processes with access to that path; a TCP socket on 127.0.0.1 is
   reachable by ANY local process/user unless an explicit auth token is
   added to every request and verified server-side. That is a real
   security surface this repo's own PII/security gates (frob check
   gate:SEC / gate:PII) would need to evaluate, not a free simplification.

DECISIONS THIS EPIC MUST MAKE BEFORE ANY CODE:
- Whether Windows daemon support is worth the effort at all (measure:
  how much wall-clock time does the daemon actually save per query on
  a representative repo? T-1093/T-1147's original daemon-latency
  measurements may already answer this for POSIX; whether it is even
  MORE valuable on Windows, given `frob check`'s own natives-build/
  subprocess overhead there, is unmeasured).
- If yes: named pipes (real Windows-native IPC, more design work) vs.
  loopback TCP+token (simpler, but a new auth surface to design and
  gate-check).
- Whether a transport abstraction (a `Transport` protocol/interface
  `_socketd.py`/`_daemon_proxy.py` code against, with a unix-socket
  implementation and a Windows implementation each satisfying it)
  should be introduced FIRST, decoupling protocol/dispatch logic from
  transport, before adding a second transport -- likely yes, since
  today's `_socketd.py`/`_daemon_proxy.py` hardcode unix-socket framing
  throughout rather than exposing a transport seam (measured in
  T-2961's assessment: "no sys.platform guard anywhere in
  src/frob/serve/ or _daemon_proxy.py; no existing Transport-shaped
  class to slot a Windows backend into").

ACCEPTANCE (placeholder, to be refined once the epic is decomposed):
a real windows-latest CI run exercises the daemon (not skipped) and the
differential-parity suite passes against a real Windows transport.

Do not close this epic without first filing its own child tickets (one
per real deliverable: transport abstraction, chosen backend
implementation, parity re-verification, doc updates) -- this ticket is
the tracking/decision record, not a single unit of work.
