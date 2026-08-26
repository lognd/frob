---
id: T-2961
title: 'Windows: ty check fails on POSIX-only stdlib attrs (socket.AF_UNIX, socketserver.ThreadingUnixStreamServer,
  os.nice)'
state: in-progress
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
- src/frob/app/_daemon_proxy.py
- src/frob/serve/_events.py
- src/frob/serve/_socketd.py
- src/frob/verify/_worker.py
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
MEASURED via a real windows-latest CI run on T-2953's PR
(https://github.com/lognd/frob/pull/3, run 32941580418, job
98093462106), after T-2953 fixed the subprocess text-mode decode
class (fcntl import crashes were already fixed by T-2952 before this).

Both prior Windows crash classes are confirmed gone in this run:
`make core` (frob natives build, including the maturin/cargo subprocess
calls) completed with no UnicodeDecodeError, and `ruff check`/
`ruff format` both passed. The pipeline reached `ty check src` --
substantially further than either of the two prior tickets got.

`ty check` (the repo's static type checker gate, run unconditionally in
CI) fails on windows-latest with 6 diagnostics, all the same shape:
POSIX-only stdlib attributes referenced unconditionally, which do not
exist in typeshed's Windows-platform view of the standard library:

  error[unresolved-attribute]: Module `socket` has no member `AF_UNIX`
    --> src/frob/app/_daemon_proxy.py:513
    --> src/frob/serve/_events.py:172
    --> src/frob/serve/_socketd.py:926
  error[unresolved-attribute]: Module `socketserver` has no member
  `ThreadingUnixStreamServer`
    --> src/frob/serve/_socketd.py:688
  error[unresolved-attribute]: Module `os` has no member `nice`
    --> src/frob/verify/_worker.py:411

This is a NEW, distinct class from both prior Windows tickets (T-2952:
bare fcntl imports; T-2953: subprocess text-mode decode defaulting to
the platform locale codec). This one is a STATIC type-check failure,
not a runtime crash -- `ty check src` genuinely cannot resolve these
attributes on Windows because AF_UNIX (Unix domain sockets),
ThreadingUnixStreamServer, and os.nice are all POSIX-only in the
standard library itself, not merely unguarded in this repo's own code.
Whether the underlying RUNTIME code paths (e.g. `_socketd.py`'s whole
unix-socket daemon) are even reachable/meaningful on Windows at all is
a separate, larger question this ticket does not attempt to answer --
this finding is scoped to "ty check src fails on windows-latest CI",
which alone blocks the CI job (and therefore blocks treating Windows
CI as green) regardless of whether the daemon itself would also need
a real Windows redesign (a named unix socket has no Windows
equivalent; TCP-on-localhost or a named pipe would be the likely
replacement, which is a design decision, not a one-line guard).

Suggested fix shape (not evaluated in depth): each of the 3 unique
call sites needs SOME platform-aware treatment -- most likely
`if sys.platform != "win32":` guards around the unix-socket-specific
code paths with a typed Windows fallback/refusal (matching this
chain's established loud-refusal-not-silent-no-op posture from
T-2918/T-2934/T-2952), and `os.nice`'s single call site
(`frob.verify._worker`) likely just needs a `hasattr(os, "nice")` guard
or a `sys.platform`-gated skip, since Windows has no direct nice-level
equivalent exposed via `os`.

Filed per this chain's own directive: "expect to find the next crash
after this one; when you do, that is success -- file it and report
it." T-2953 remains scoped to subprocess text-mode decoding; this is a
new, unrelated defect discovered only by getting past that class.

Acceptance: a real windows-latest CI run gets past `uv run ty check
src` with zero diagnostics (or the daemon/worker code paths are
restructured such that ty can resolve every attribute it type-checks
on a Windows target).
