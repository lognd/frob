---
id: T-3331
title: FLAGCOV001 can only ever measure frob itself (diax F-008)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_flag_coverage.py
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
Found in ../diax FROBLEMS.md (F-008), confirmed live during T-3277's
re-measurement: FLAGCOV001 reports UNRESOLVED on every freshly scaffolded
project checked in this session (python-tool, python-library), with:

  FLAGCOV001: no [[docblocks.commands]] entries declared in frob.toml --
  flag-coverage cannot determine this project's CLI surface at all; this
  is an UNMEASURED project, not a clean pass.

Per the diax report, the underlying defect is structural: FLAGCOV001
tries to import the CONSUMER project's own package from inside frob's
own uv-tool venv (the global `uv tool install frob` environment), so it
can only ever successfully measure frob's own CLI surface, never a
scaffolded/consumer project's. NOT re-verified line-by-line against the
gate's source in this ticket (out of T-3277's scope) -- filing so it is
tracked and someone can confirm the root cause against
src/frob/gates/_flag_coverage.py directly.

Currently the ONLY UNRESOLVED gate left on a freshly-scaffolded,
otherwise-fully-fixed python-tool project (T-3277) -- everything else is
0 errors/0 warnings. `frob check`'s overall exit code is unaffected by an
UNRESOLVED-only gate (does not block "0 errors"), so this is not blocking
T-3277's green DX test, but it is a real "cannot measure" defect a new
user's first `make check` output will show.
