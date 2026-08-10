---
id: T-1995
title: 'frob ticket new does not surface existing or archived coverage: 7 tickets
  filed and dropped this session, several costing a dispatch'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket new` accepts any ticket without checking whether the work is
already tracked or already done. Seven tickets filed this session had to
be dropped, and several cost a dispatched agent a full cycle to discover
there was nothing to do.

MEASURED -- all seven dropped, with the reason each was unnecessary:
  T-1915  duplicate of open T-1867
  T-1991  duplicate of open T-1989 (same 105 findings)
  T-1986  duplicate of ALREADY-LANDED T-1866 -- the feature it asked for
          (`_refuse_over_broad_scope_on_start`, app/ticket_runner/
          _lifecycle.py:912) already existed and its tests passed
  T-1972  already resolved by REG010's existing Tier-A auto-fix, which
          had run during another ticket's land
  T-1947  already fixed by T-1954 + T-1951 before anyone read it
  T-1976  its only outstanding item already existed on main
  T-1949  already split by T-1933; function measured 41 lines, under the
          60-line threshold it claimed to exceed

COST: T-1972 and the T-1976/T-1949 pair each consumed a dispatch. T-1986
was filed at HIGH and competed for a dispatch slot against genuinely
starved work. A stale or duplicate ticket does not merely waste its own
slot -- it displaces real work at the top of the queue.

TWO DISTINCT MISSES, and the second is the one nothing covers:
1. Duplicate of an existing TICKET. The standing pre-filing search covers
   open tickets, which catches T-1915/T-1991 if actually run.
2. Duplicate of an already-SHIPPED capability. T-1986 asserted "nothing
   enforces X" when X had shipped two days earlier. Searching open
   tickets cannot catch this -- the covering ticket was DONE and
   archived. This class needs a code check, not a queue check.

THE RULE EXISTS AND IS ALREADY FOLLOWED. The standing dispatch duty says
to search for an existing ticket including in-progress and queued before
filing. That search WAS run before T-1986 and returned nothing, correctly,
because the covering work was archived. So a louder instruction cannot
fix class 2 -- the search was performed and was looking in the wrong
place.

DO NOT FIX IT THIS WAY:
- Do NOT block `ticket new` on a similarity heuristic alone. False
  positives on genuinely-new tickets would be worse than the current
  cost, and near-duplicate titles are common and often legitimate
  (successor tickets, per-node burn-downs, sweep-filed regressions).
- Do NOT auto-close/auto-drop a suspected duplicate. Disposition needs a
  human or agent judgement; the harm here was wasted dispatch, not a
  corrupted ledger.
- Do NOT limit the check to open tickets. That is exactly the gap that
  let T-1986 through.

FIX DIRECTION, preferred order:
(a) At `ticket new`, surface likely-related tickets -- INCLUDING done and
    archived -- and require an explicit acknowledgement to proceed. The
    ledger is local and already indexed; this is a read, not a new
    subsystem.
(b) For a ticket whose body asserts a missing enforcement ("nothing
    refuses / only warns / is not checked"), additionally surface any
    matching rule id, `_refuse_*`/`_check_*` symbol, or test name found
    in the tree, so the author sees the existing implementation before
    filing.

ACCEPTANCE: first test must FAIL before the fix -- file a ticket whose
title closely matches an ARCHIVED done ticket and assert the related
ticket is surfaced by id. Then assert a genuinely novel ticket files
without friction, and that a successor ticket deliberately similar to its
predecessor can still be filed after acknowledgement.
