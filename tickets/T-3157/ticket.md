---
id: T-3157
title: Ground-truth fixture suite for scripts/fleet_status.py
state: in-progress
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/**/test_fleet_status*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: scripts/fleet_status.py
  reason: T-3152 holds a live write lease on this file; the fixture suite only needs
    read access to fleet_status.py from tests/, not write scope on the file itself
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Four separate defects were found in scripts/fleet_status.py in a single day
(2026-08-27):

(a) _FROB_CHECK_TOKEN_RE never matched 'python -m frob check', so running
    checks were invisible to the tool.
(b) The LAND LOCK line reported fd-open waiters as holders (fixed T-3093 by
    reading /proc/locks).
(c) A false LEAK was reported against a live registered worktree (fixed
    T-3128).
(d) Orphan forkserver counting applied no age floor while
    reap_orphaned_forkservers has always applied a 300s
    DEFAULT_ORPHAN_AGE_FLOOR_S, so a seconds-old forkserver spawned by a
    live pytest-xdist run was reported ORPHANED on sight (fixed T-3139).

A fifth divergence is already filed separately as T-3152 (age computed via
dir-mtime in _reap.py vs stat-starttime in fleet_status.py) -- do not
duplicate that fix here, this ticket is about test infrastructure, not a
sixth point-fix.

The file also carries a LARGE001 waiver.

Cost of (a): it caused a relay of "23 orphaned forkservers" and "13
climbing" to the repo owner as fact. Both numbers were substantially
measurement artifacts of the missing age floor and token-match bug. This
tool is what the coordinator STEERS THE FLEET BY -- when it lies, the fleet
is dispatched on fiction. That is the real cost, and it is why a fifth
point-fix is the wrong response; the file needs a dedicated ground-truth
test suite instead of continued reactive patching.

Scope: a new ground-truth fixture suite for scripts/fleet_status.py --
constructed /proc trees and real git worktrees exercising each thing
fleet_status claims to observe:
  - checks running (token match against real invocation strings, e.g.
    'python -m frob check', 'uv run frob check', bare 'frob check')
  - land lock holders vs waiters (via /proc/locks fixtures)
  - worktree leases and leaks (via real git worktree fixtures, live vs
    stale/removed)
  - orphaned forkservers (via constructed /proc/<pid> trees with controlled
    start times, both under and over DEFAULT_ORPHAN_AGE_FLOOR_S)

For each claim: a must-fire case (the condition is real and fleet_status
must report it) AND a must-stay-quiet case (the condition looks similar but
is NOT the thing, and fleet_status must NOT report it).

Acceptance denominator: every one of the four defects above (a, b, c, d)
must be expressible as a fixture in this suite -- i.e. each one, injected
into the parent commit predating its fix, must make the corresponding new
fixture test FAIL. If the suite would not have caught all four, it is not
done.
