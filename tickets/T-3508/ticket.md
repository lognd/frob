---
id: T-3508
title: Fix AF_UNIX degradation-direction asserts and verify the loud Windows refusal
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
blocked_by:
- T-2963
parent: T-3505
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_daemon_proxy.py
- src/frob/serve/_socketd.py
- src/frob/serve/_events.py
- tests/test_app_daemon_proxy.py
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
Fix the direction of the platform-degradation assertions around
socket.AF_UNIX so the daemon proxy's existing loud-refusal path is
correctly exercised and verified on Windows, WITHOUT taking on
T-2963's full transport-abstraction epic.

MEASURED: 10 of T-3076's 278 windows-only failures are
AttributeError: module 'socket' has no attribute 'AF_UNIX', concentrated
in tests/test_app_daemon_proxy.py (10 of that file's failures per
T-3076's by-file breakdown). T-3076 additionally flags a DISTINCT
sub-class of failure in this area: tests asserting the platform-
degradation enum the WRONG direction (e.g. `assert
DaemonLiveness.PlatformUnsupported is DaemonLiveness.<other>` and
`assert ProxyReason.PlatformUnsupported is ProxyReason.<other>`) --
these are cheap, already know about the boundary, and disagree with
the code about which side Windows is on. Fix those as part of this
leaf per T-3076's own instruction to separate them out.

DESIGN: per T-2963 (the Windows-native-transport epic, explicitly
OUT of 1.0.0 scope), the daemon is already meant to refuse loudly and
safely on Windows rather than crash at import or touch AF_UNIX at all
-- T-2961 already made src/frob/app/_daemon_proxy.py and
src/frob/serve/_socketd.py guard the AF_UNIX touch behind a Windows
check before constructing the socket. This leaf is NOT about building
a real Windows transport (that stays T-2963's job, post-1.0.0 per its
own body). It is about (a) making the existing guard actually prevent
the AttributeError on a live Windows run/CI, and (b) correcting the
degradation-enum assertions T-3076 identified as backwards.

FILES IN SCOPE:
  src/frob/app/_daemon_proxy.py
  src/frob/serve/_socketd.py
  src/frob/serve/_events.py
  tests/test_app_daemon_proxy.py

MUST-FIRE
- On Windows, no code path constructs socket.AF_UNIX; every caller
  hits the documented loud ProxyReason.PlatformUnsupported /
  DaemonLiveness.PlatformUnsupported refusal instead of an
  AttributeError.
- The degradation-direction assertions in test_app_daemon_proxy.py (and
  any sibling files T-3076's log shows the same pattern in) assert the
  correct enum member.
- The 10 windows-only AF_UNIX failures collapse.

MUST-STAY-QUIET
- POSIX AF_UNIX behavior (real unix-socket daemon transport, existing
  differential-parity suite) is unchanged.
- Does not expand into T-2963's transport-abstraction/named-pipes/TCP+
  token work -- that stays a separate, explicitly post-1.0.0 epic per
  T-2963's own body. If this leaf's investigation finds the loud-refusal
  guard is structurally insufficient without T-2963's transport seam,
  STOP and report back rather than absorbing epic-sized work here.

SCOPE GROUPING: scope-disjoint from the fcntl, os.sysconf, fork-context
and charmap leaves -- dispatchable in parallel with all four.
