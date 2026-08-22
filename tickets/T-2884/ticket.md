---
id: T-2884
title: Daemon version-skew self-heal is version-string-based, blind to source-only
  changes with no version bump
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
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
- src/frob/serve/_socketd.py
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
## The gap

`frob.app._daemon_proxy.ensure_daemon`'s self-healing version skew check
(T-1093/T-1105) compares the daemon's self-reported `daemon_version()`
against the CLI client's own `_client_version()` -- both computed via
`importlib.metadata.version("frob")`, i.e. the INSTALLED DISTRIBUTION's
declared version string from package metadata, not the actual source
content the running interpreter loaded.

`frob.serve._tools.frob_check_delta`/`frob_check_scope` run ONLY inside
this long-lived warm daemon process (confirmed: `frob.serve._tools.py`'s
own module comment "T-1436: frob_check_delta only ever runs inside the
warm daemon process"). Because a Python interpreter never re-imports a
module just because the file on disk changed, a daemon process that was
already running BEFORE a source-only fix landed keeps executing the OLD,
pre-fix code for its entire remaining lifetime -- and the skew check has
no way to detect this, because a source-only change with no version bump
leaves BOTH `daemon_version()` and `_client_version()` reporting the exact
same string forever.

Directly relevant: T-2849 (this repo's own PDEATHSIG forkserver-leak fix)
changed `src/frob/gates/__init__.py` and `src/frob/process/_reap.py` but
did not touch `pyproject.toml` (verified: `git show --stat
5dad1ad96008f66d9b169a001a1464aaabed8083` lists no version file). Any
daemon process that predates that land would silently keep running the
pre-fix `_open_process_pool` (no env stamp, no PDEATHSIG initializer)
forever, immune to the self-healing restart T-1093/T-1105 were built to
provide, and undetectable by the client -- `ensure_daemon` would read
`Live`, never `VersionSkew`, for exactly this case.

## What to determine

1. Whether `daemon_version()`/`_client_version()` should instead reflect
   something content-sensitive -- e.g. a hash of the installed package's
   `RECORD`/site-packages tree, or an explicit "source changed since I
   started" self-check the daemon can run against its own `__file__`
   mtimes at a bounded interval -- rather than the package version alone.
2. How often this repo's own source changes WITHOUT a version bump (this
   repo bumps a version stamp `REL001`-style only for public API surface
   changes; a private-helper-only fix, or a fix like T-2849's that adds a
   new public symbol without triggering REL001, would not bump it) --
   that rate bounds how exposed this gap actually is in practice.
3. Whether the daemon is enabled anywhere in this fleet's real usage
   today (`_daemon_enabled()` requires `FROB_DAEMON=1`; not found set in
   `scripts/`, `.claude/`, or `Makefile` as of this filing) -- if truly
   unused, this is a latent landmine rather than an active one, still
   worth closing before the opt-in flag is ever flipped on by default.

## Positive controls

- A daemon started from a git ref BEFORE some public-symbol-only source
  change (no version bump) should be detected as skewed (or otherwise
  restarted) once that change lands, without any version string changing.
- A daemon started from the SAME ref as the client should be reported
  `Live`, not incorrectly restarted.

## Origin

Found while investigating T-2880 (frob check forkserver leak persisting
after T-2849) -- ruled out as T-2880's own dominant cause (the daemon is
opt-in and not observed enabled anywhere in this fleet's config), but
independently confirmed as a real defect by direct code reading, filed
separately since its fix lives in `src/frob/app/_daemon_proxy.py` /
`src/frob/serve/_socketd.py`, outside T-2880's declared scope.
