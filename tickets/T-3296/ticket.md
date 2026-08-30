---
id: T-3296
title: frob-coverage.lock.json scope-lease deadlock blocks TEST006 for every ticket
  but one
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_scope.py
- src/frob/gates/_coverage.py
- src/frob/gates/__init__.py
- tests/test_tickets_scope_mutation.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: must-fire/must-stay-quiet tests for the frob-coverage.lock.json scope-lease/SCOPE001
    exemption this ticket adds
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_gates.py
  reason: must-fire/must-stay-quiet tests for the frob-coverage.lock.json scope-lease/SCOPE001
    exemption this ticket adds
  actor: logan
  at: '2026-08-29'
evidence:
- tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_frob_managed_side_effect_path_never_conflicts
- tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_non_exempt_path_still_conflicts_alongside_exempt_one
- tests/test_gates.py::TestScopePrework::test_scope001_frob_managed_side_effect_path_never_fires
- tests/test_gates.py::TestScopePrework::test_scope001_still_fires_for_non_exempt_unscoped_file_alongside_exempt_one
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-029, F-039, F-042,
frob 0.530.0, 2026-08-28). Three separate reports, one root cause: a single
tracked frob-coverage.lock.json can be scope-leased by only one in-progress
ticket at a time (src/frob/tickets/_scope.py::scope_lease_conflict), but
TEST006 tells EVERY ticket to run `make coverage && frob check
--stamp-coverage`, and --stamp-coverage rewrites that same tracked path
(src/frob/gates/_coverage.py::write_coverage_lock, called from
src/frob/gates/__init__.py around line 4952-5001, _COVERAGE_LOCK_REL =
"frob-coverage.lock.json").

CONFIRMED IN CODE: no exemption for frob-coverage.lock.json exists in the
scope-lease path (src/frob/tickets/_scope.py, _validate_scope_mutation /
scope_lease_conflict) or in the SCOPE001 gate (src/frob/gates/__init__.py,
search "SCOPE001"). The lock is treated as an ordinary tracked path like any
project file.

THE DEADLOCK, as three separate reporters hit it independently:
  - F-029: T-0027 tried `scope --add frob-coverage.lock.json` while T-0045
    held it -- ScopeLeaseConflict. Workaround: stamp locally (satisfies
    TEST006 via .frob/ cache), then `git checkout main -- frob-coverage.lock.json`
    to leave the tracked file untouched, then commit the restoration.
  - F-039: same shape from the other side -- T-0022 stamped while T-0015 held
    the lease; had to `git checkout frob-coverage.lock.json` afterward, discarding
    its own real stamp.
  - F-042: no clean exit either way -- keep the rewritten lock and SCOPE001
    fires (file outside scope); revert it and TEST006 fires (stamp stale).
    Under any parallel/fleet workflow (this repo runs several agents
    concurrently as a matter of course), exactly one in-progress ticket can
    ever own the coverage lock; every other one is structurally unable to
    satisfy TEST006 through the documented path.

WHAT NOT TO DO: do not "fix" this by granting every ticket an implicit
scope grant on frob-coverage.lock.json (that just changes ScopeLeaseConflict
into silent last-writer-wins clobbering between concurrent stampers, which is
worse -- a stamp from ticket A's tree could get overwritten by ticket B's
unrelated coverage run and now records the WRONG ticket's numbers). Do not
special-case only this one path name either -- the same shape will recur for
any other frob-managed tracked file a gate rewrites as a side effect (see the
related SCOPE001-exemption ticket for tickets/**; coordinate, don't duplicate
the exemption list).

WHAT TO BUILD: pick one and state which, then implement it:
  (a) frob-coverage.lock.json is exempt from scope leasing outright (SCOPE001
      does not fire on it, `scope --add` never needs to claim it), and
      --stamp-coverage's write goes through a merge/regenerate step at land
      time instead of racing multiple in-progress trees; OR
  (b) the coverage lock becomes per-ticket (e.g. keyed by ticket id, merged
      at archive/land) so concurrent stampers never collide.
Either way, TEST006 must be satisfiable by MORE than one in-progress ticket
at a time -- that is the actual defect; the exact mechanism is a design
choice, but "only one ticket in the whole repo can ever pass TEST006" is not
acceptable for a tool whose own documented workflow runs tickets in parallel.

MUST-FIRE FIXTURE: two ticket worktrees, both in-progress, both scoped to
disjoint source paths; both run `make coverage && frob check
--stamp-coverage`; both must be able to record a passing TEST006 stamp
without a ScopeLeaseConflict and without silently discarding either's real
coverage numbers.

MUST-STAY-QUIET FIXTURE: a single ticket, alone, stamping coverage exactly as
today -- must keep working with no new friction (no new consent prompt, no
new required flag).