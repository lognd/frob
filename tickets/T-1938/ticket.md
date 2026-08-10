---
id: T-1938
title: 21 byte-identical copies of the RELWAIVE002 stale-waiver block across strata
  (DUP001 type-name blind spot)
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

21 strata modules each carry a BYTE-IDENTICAL copy of the stale-waiver
emit block, differing only in the violation dataclass they construct:

    stale = tuple(
        <XxxViolation>(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            sub_target=stale_waiver.rule,
            detail=(f"waive {stale_waiver.rule!r} on node {stale_waiver.node} "
                    f"reason={stale_waiver.reason!r} is stale -- no matching "
                    f"finding fired this run"),
        )
        for stale_waiver in applied.stale
    )

Verified identical in `_backpressure.py` and `_fallback.py`; all 21
modules that mention RELWAIVE002 also contain a `stale = tuple(` block
(21/21 both counts).

WHY IT MATTERS: this is the exact NO-DUPLICATION failure the global rules
name -- one rule with 21 homes. The message text, the sub_target
convention, and the staleness semantics all have to be edited 21 times
to stay consistent, and nothing detects a partial edit. It is also a
DUP001 MISS worth understanding in its own right: the blocks differ only
in a TYPE NAME, so a syntactic duplicate detector does not see them.
That is precisely the "dup type-generalize" pillar recorded in the
static-quality-vision tree (T-0287..0290) -- so this is both a cleanup
and a live test case for that detector.

Two deliverables, and the second is the load-bearing one:
1. Extract the block to one generic helper the 21 call sites share.
2. Confirm whether DUP001 can be generalized to catch type-name-only
   duplication. If it can, this family is its regression corpus; if it
   cannot, say so explicitly rather than leaving it implied.