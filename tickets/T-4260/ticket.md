---
id: T-4260
title: TDD001 reports a self-referential tests edge as an unfixable ordering violation
  and a backwards edge as a reorder instruction
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tdd_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a tests edge whose source and target are the same symbol, when TDD001
    runs, then it reports a malformed directive naming the file to correct rather
    than an ordering violation no reordering can clear
  evidence: []
- text: given a tests edge whose source is a test and whose target is production code,
    when TDD001 runs, then it reports the directive as written backwards rather than
    an ordering result computed from swapped roles
  evidence: []
- text: given the two malformed-edge cases, when the fix lands, then neither is resolved
    by waiving the observed instances
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TDD001 EMITS AN INCOHERENT, UNFIXABLE FINDING WHEN A TESTS EDGE POINTS AT ITSELF,
AND A MISLEADING ONE WHEN THE EDGE IS WRITTEN BACKWARDS. Measured on a real land
attempt, in a batch of 21 findings over 21 edges.

WHAT WAS OBSERVED. Two findings named the SAME symbol on both sides, reading
that a test was not committed strictly after its verifying test, where the
verifying test named was that identical test. Several others named a test symbol
as the artifact and a production symbol as the verifying test, which is the
binding written backwards.

WHY IT HAPPENS, READ FROM THE CODE RATHER THAN INFERRED. The gate consumes
tests-kind edges verbatim: the edge source is treated as the implementation and
the edge target as the test, with no check that those roles are plausible. The
order classifier then treats two identical commits as a determinate
implementation-first violation, which is the right call for a genuine pair. But
a self-referential edge resolves BOTH sides to the same introducing commit by
construction, so it is classified as a violation unconditionally, on every run,
forever. There is no ordering a person could establish that would clear it. The
only exit is a waiver, which makes this the no-exit shape: a rule demanding
something the subject structurally cannot provide.

THE MESSAGE IS ALSO UNACTIONABLE ON ITS OWN TERMS. It advises writing the test
before the implementation it verifies. When both names are the same symbol that
advice cannot be followed, and when the roles are reversed it tells the reader to
reorder a pair whose real defect is that the directive names the wrong direction.
A reader who follows the advice literally will reorder commits and the finding
will not clear.

WHAT THE FIX SHOULD DO. Validate the edge before classifying its order. An edge
whose source and target are the same symbol is a malformed directive, not an
ordering violation, and should say so and name the file and directive to correct.
An edge whose source is a test and whose target is production code is a directive
written backwards, and should say that instead of reporting an ordering result
computed from swapped roles. Decide deliberately whether these belong to TDD001
as distinct messages or to whatever validates directives at parse time; the
parse-time home is likely better, because a malformed directive is wrong the
moment it is written and should not wait for a land to be noticed.

DO NOT FIX THIS BY WAIVING THE INSTANCES. The instances are the evidence.
