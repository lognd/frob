---
id: T-4088
title: PERF003 reports nested loops for two SEQUENTIAL loops, failing the self-gate
  on both posix legs (AST proves no nesting)
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/__init__.py
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
PERF003 REPORTS "NESTED LOOPS" FOR TWO SEQUENTIAL LOOPS IN ONE FUNCTION. It is
currently the SOLE ERROR failing the self-gate on BOTH ubuntu and macOS, and it is
provably wrong.

THE FINDING:

    [gate:PERF] tests/test_serve_socket.py:347  PERF003  nested loops with an
    equality comparison; suggested fix: index the inner collection by the
    compared key

THE PROOF THAT IT IS FALSE. An AST walk over the flagged function reports no
nesting whatsoever:

    test_serves_one_request_then_idle_exits (line 357): 2 loops, nested pairs=[]

The two loops are SEQUENTIAL, not nested -- a socket-reachability poll followed by
a thread-death poll:

    while not socket_path(root).exists() and time.monotonic() < deadline:
        ...
    ...
    while thread.is_alive() and time.monotonic() < deadline:
        thread.join(timeout=0.1)

There is no inner collection, no quadratic behaviour, and no key to index by. The
suggested remedy -- "index the inner collection by the compared key" -- is
inapplicable to a wall-clock poll, which is itself a strong signal the detector
matched a shape it does not understand.

HOW IT GOT HERE, AND WHY THAT MATTERS. The second loop was added TODAY by T-4055,
which fixed a real flake by replacing `thread.join(timeout=5)` plus
`assert not thread.is_alive()` with a poll-until-dead-or-deadline loop. That fix
is correct and was verified 15/15 clean at -n 4. So a CORRECT FIX FOR A REAL
DEFECT TRIPPED A FALSE POSITIVE, and the gate now blocks both posix legs from
green. Confirmed by comparison: gate:PERF read "pass, 0 errors, 81 warnings" on
the earlier run (ca586645c) and reads "FAIL, 1 error, 81 warnings" now.

NOTE ANOTHER FUNCTION IN THE SAME FILE ALSO HAS TWO SEQUENTIAL LOOPS AND DOES NOT
FIRE: test_n_racing_callers_exactly_one_wins (line 152), 2 loops, nested pairs=[].
So the detector is not simply counting loops per function -- something about the
equality-comparison half selects one and not the other. DETERMINE WHAT ACTUALLY
TRIGGERS IT before fixing; the difference between those two functions is the
shortest path to the real predicate.

THE LINE NUMBER IS ALSO SUSPECT AND WORTH CHECKING: the finding is reported at
line 347, which in that revision is inside a `@pytest.mark.skipif` reason STRING,
several lines above the enclosing class. If PERF003 reports an enclosing-symbol
line rather than the offending construct's line, that is a second, separate defect
-- a finding a reader cannot navigate to. Confirm which it is.

DO NOT fix this by weakening PERF003 generally. Genuine nested-loop-with-equality
is a real performance smell and the rule should keep catching it. The defect is
that the predicate matches non-nested code.

INTERIM: the site is waived with this ticket as follow_up, because the finding is
demonstrably false and it is blocking both posix legs. That waiver should be
REMOVED when the predicate is fixed -- it documents a detector bug, not a code
decision, and this queue has repeatedly recorded that waivers written for tooling
reasons outlive their cause (T-4054, T-4063, T-4064).

MUST-FIRE FIXTURE: a genuinely nested loop pair with an equality comparison over a
collection is still flagged.
MUST-STAY-QUIET: two sequential polling loops in one function are not flagged.
THIRD FIXTURE: the reported line points at the offending construct, not at an
enclosing symbol or a decorator string.

ACCEPTANCE
- The real trigger determined by comparing the two same-shaped functions, one of
  which fires and one of which does not.
- Sequential loops no longer reported as nested.
- The line-number question answered.
- The interim waiver removed as part of the fix.
- All three fixtures committed.