---
id: T-2981
title: windows-latest CI fails at Typecheck on main after passing native build, both
  cargo suites and lint
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: high
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
- docs/modules/serve.md
- docs/modules/testing.md
evidence_scope:
- tests/test_serve_socket.py
- tests/unit/test_daemon_proxy_lease_t1276.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/**
  reason: windows typecheck fix scoped to daemon server + proxy
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: windows typecheck fix scoped to daemon server + proxy
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/serve.md
  reason: doc edges referenced by scoped symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/testing.md
  reason: doc edges referenced by scoped symbols
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: set
  reason: pulled the real windows-latest job log via the job-scoped API and recorded
    the 14 actual ty diagnostics plus their root cause, so whoever picks this up does
    not have to re-fetch and re-derive them
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 4219
- mode: append
  reason: T-2981 is a typing-only fix with no runtime behavior change; BUG002 requires
    either a real repro or this directive, and a real repro is impossible for a pure
    type-checker finding
  actor: logan
  at: '2026-08-26'
  old_length: 4218
  new_length: 5534
evidence:
- tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Pulled from the real windows-latest job log (run 32968539246, job 98176563543,
main, push trigger). The job passed checkout, uv, Rust, cargo cache, sync deps,
native extension build, `cargo test` for BOTH frob-core and strata-core, and
Lint -- then failed at Typecheck with **14 diagnostics**, every one of them an
`unresolved-attribute`:

    error[unresolved-attribute]: Object of type `Self@call` has no attribute `_sock`   (x2)
    error[unresolved-attribute]: Object of type `Self@close` has no attribute `_sock`
    error[unresolved-attribute]: Object of type `_DaemonServer` has no attribute `idle_tracker`   (x2)
    error[unresolved-attribute]: Object of type `_DaemonServer` has no attribute `root`
    error[unresolved-attribute]: Object of type `_DaemonServer` has no attribute `event_bus`      (x3)
    error[unresolved-attribute]: Object of type `_DaemonServer` has no attribute `lease_manager`  (x3)
    error[unresolved-attribute]: Object of type `_DaemonServer` has no attribute `shutdown`       (x2)
    Found 14 diagnostics

ROOT CAUSE. These are a direct consequence of T-2961's own Windows guard, not a
pre-existing defect. T-2961 made `_DaemonServer` conditional so the module stops
raising `AttributeError` at import time on Windows (the real bug it fixed), and
bound a Windows placeholder to keep the name defined. But the placeholder does
not carry the attributes the real `socketserver.ThreadingUnixStreamServer`
subclass carries -- `idle_tracker`, `root`, `event_bus`, `lease_manager`,
`shutdown` -- so on Windows every attribute access against it is unresolved. The
three `_sock` diagnostics are the same shape in the client half
(`_daemon_proxy`), where the socket assignment now sits inside a platform guard.

WHY IT WAS NOT CAUGHT BEFORE LANDING, and this is the transferable lesson:
T-2961 was verified locally with `uv run ty check src` exiting 0, and that
verification was STRUCTURALLY INCAPABLE of catching this. A type checker
evaluates `sys.platform` conditionals per target platform: on Linux it takes the
POSIX branch and never analyses the Windows placeholder branch at all. A local
`ty check` on Linux therefore cannot validate Windows-only code paths, no matter
how careful the author is. Only a Windows type-check run -- or an explicitly
Windows-targeted check -- can.

The T-2961 Done report was honest that it could not reach real CI (blocked at
the time by an unrelated lint regression, since fixed) and did not claim
CI confirmation. This ticket is the confirmation arriving late and disagreeing.

WHAT IS WANTED
- Make the Windows placeholder carry the same public attribute surface the real
  `_DaemonServer` exposes, or restructure so the attribute accesses are not
  reachable on Windows at all. A Protocol/ABC declaring the surface, with both
  the real class and the Windows stub conforming, is the shape most likely to
  satisfy the checker on BOTH platforms without duplicating behaviour.
- Same treatment for the `_sock` accesses in the client half.
- Do NOT silence these with blanket `ty: ignore`. That converts a real
  platform-divergence signal into an invisible gap, which is the failure class
  this repo has spent a whole drive eliminating. A targeted ignore is acceptable
  only where the runtime is already provably guarded AND the reason is written
  next to it (the `os.nice` precedent under T-2961 is the acceptable form).

ACCEPTANCE
- Given windows-latest CI, when Typecheck runs, then it reports 0 diagnostics.
  Proven by a REAL windows-latest run, not a local check -- local Linux `ty` is
  structurally incapable of proving this, as above.
- Given ubuntu-latest and macos-latest, when Typecheck runs, then their
  diagnostic counts are unchanged. Report before/after for all three.
- Given the fix, when the daemon runs on a POSIX platform, then behaviour is
  unchanged -- this is a typing/structure fix, not a behaviour change.

FOLLOW-ON WORTH CONSIDERING (file separately, do not scope-creep this ticket):
every platform-conditional branch in the repo has this same blind spot under a
single-platform type check. A CI step that runs `ty` with an explicit Windows
target from Linux would catch this class before it reaches a Windows runner.

frob:no-behavior-change reason="T-2981 is a typing/structure-only fix: it declares a Protocol (_DaemonServerLike) and a class-level attribute annotation (_LeaseConnection._sock) so ty check resolves the daemon server's attribute surface identically on every sys.platform target. No runtime code path, branch, or behavior changes on any platform -- run_socket_daemon's Windows refusal and the real POSIX _DaemonServer class body are both untouched. The defect this ticket fixes is a CI type-checker diagnostic (14 unresolved-attribute findings under a Windows-target ty check), not a runtime bug reachable by any test -- there is no runtime path to make a pytest test fail at main and pass at the fix, since nothing at runtime changed. The evidence bound (tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits, tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close) is a regression guard proving the touched runtime paths still work identically, matching this directive's own must-still-pass requirement. The real proof of the fix is `uv run ty check --python-platform win32 src` going from 14 diagnostics to 0, reported in the Done report -- not a pytest repro, because the defect is a type-checker finding, not a runtime one."