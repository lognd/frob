---
id: T-3307
title: RENDER001 fires on scaffold's own scripts/bump_version.py print
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/scripts/bump_version.py.j2
- src/frob/gates/__init__.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-016).

RELATED, DO NOT DUPLICATE: T-3277 (queued) already covers the broader
"fresh scaffold fails its own make check" bug (F-005), enumerating
*SCHEMA001, REF001/REF002, OPAQUE001, COV001, TEST003, ROOT001, PRE001/
SCOPE001. RENDER001 on scripts/bump_version.py's `print(new)` was NOT in that
enumeration and is a distinct gate; file it separately and note the
T-3277/T-3273 relationship in this ticket so whoever picks it up coordinates
rather than colliding on the scaffold template files.

The scaffold's own `scripts/bump_version.py` prints the new version to
stdout by design -- the generated Makefile's `upload` target captures that
output. RENDER001 flags it on every `make check`/land as a bare stdout write.
Either the scaffold template should ship a `frob:waive RENDER001` on that
line, or RENDER001 should exempt `scripts/` (confirm which is the right
call -- an unscoped `scripts/` exemption may be too broad; check what
RENDER001 actually guards against before picking).

MUST-FIRE FIXTURE: a non-scripts print statement outside any deliberate
CLI-output path -- RENDER001 must still fire.

MUST-STAY-QUIET FIXTURE: a freshly scaffolded python-tool project's
`make check` -- 0 RENDER001 findings on scripts/bump_version.py.
