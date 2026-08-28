---
id: T-3180
title: Scope-lease overlap check refuses provably-disjoint globs (literal accepted,
  wildcard refused)
state: in-progress
kind: bug
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
- src/frob/tickets/_scope.py
- src/frob/tickets/_models.py
- tests/test_tickets_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_scope.py
  reason: the glob-vs-glob lease overlap predicate lives here
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_models.py
  reason: fix lives in _globs_intersect (_models.py), imported by _scope.py; test
    file for the fixtures
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_tickets_lease.py
  reason: fix lives in _globs_intersect (_models.py), imported by _scope.py; test
    file for the fixtures
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 while scoping T-3179. The scope-lease overlap check refuses
a requested glob that CANNOT share any path with the leased glob it names.

EXACT REPRO (T-3157 held `tests/**/test_fleet_status*.py`, in-progress):

    $ frob ticket scope T-3179 --add 'tests/unit/verify/test_nonexistent_xyz*.py'
    ERROR: tickets: T-3179 cannot lease an add glob: held by in-progress T-3157
      (scope 'tests/**/test_fleet_status*.py')
    ERROR: scope change failed: ScopeLeaseConflict: requested --add glob
      overlaps a path leased by another in-progress ticket

No filesystem path matches both `tests/unit/verify/test_nonexistent_xyz*.py` and
`tests/**/test_fleet_status*.py`. The basenames are disjoint literals up to
their wildcards. The intersection is provably empty.

THE DISCRIMINATING OBSERVATION -- literal accepted, wildcard refused. In the
same session, against the same held lease:

    --add 'tests/unit/verify/test_attribution.py'    ACCEPTED
    --add 'tests/unit/verify/test_attribution*.py'   REFUSED
    --add 'tests/unit/verify/test_nonexistent_xyz*.py'  REFUSED

So the defect is not in path resolution generally; it is specific to the
glob-vs-glob case. The check appears to reduce a wildcard-bearing request to its
directory prefix (or otherwise treat any `*` as "matches anything under here")
and then test that prefix against the leased pattern, rather than deciding
whether the two PATTERNS can intersect.

WHY THIS MATTERS BEYOND THE ANNOYANCE. Guard breadth serializes dispatch. A
lease refusal that over-approximates makes unrelated tickets mutually exclusive:
any in-progress ticket holding a `tests/**/...` glob blocks every other ticket
from leasing any wildcard test glob anywhere in the tree. Under a multi-agent
fleet that converts parallel work into serial work for no reason, and the
failure is silent about being spurious -- it names a real ticket and a real
lease, so it reads as a legitimate conflict.

The workaround (enumerate literal paths) is worse than it looks: it defeats the
purpose of glob scopes and produces scopes that silently fail to cover
newly-added files.

DO NOT SOLVE THIS BY WEAKENING THE LEASE. Leases prevent two agents writing the
same file concurrently, which is a real and repeatedly-observed hazard here. The
fix is to decide pattern INTERSECTION correctly, not to refuse less often in
general. An overlap check that under-approximates would let two agents lease the
same file and is strictly worse than the current over-approximation.

ACCEPTANCE
- A pattern-intersection predicate that decides whether two globs can share any
  path, replacing the current prefix-based approximation.
- MUST-FIRE fixtures: genuinely overlapping glob pairs are still refused --
  including `tests/**/a*.py` vs `tests/unit/ab.py`, and identical globs, and a
  `**` that genuinely subsumes the other pattern.
- MUST-STAY-QUIET fixtures: the three measured cases above, plus disjoint
  basenames under a shared `**` prefix.
- Confirm the refusal message still names the holding ticket and its glob when
  it does fire.
