---
id: T-1938
title: 21 byte-identical copies of the RELWAIVE002 stale-waiver block across strata
  (DUP001 type-name blind spot)
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_backpressure.py
- src/frob/strata/_circuit_breaker.py
- src/frob/strata/_clock_ordering.py
- src/frob/strata/_delivery_semantics.py
- src/frob/strata/_distributed_txn.py
- src/frob/strata/_fallback.py
- src/frob/strata/_interactive_cost.py
- src/frob/strata/_message_schema.py
- src/frob/strata/_observability.py
- src/frob/strata/_process_bounds.py
- src/frob/strata/_reliability.py
- src/frob/strata/_retry.py
- src/frob/strata/_shared_state.py
- src/frob/strata/_slo.py
- src/frob/strata/_spof.py
- src/frob/strata/_ssot.py
- src/frob/strata/_starvation.py
- src/frob/strata/_supply_chain_boot.py
- src/frob/strata/_sync_depth.py
- src/frob/strata/_txn.py
- src/frob/strata/_waive.py
- tests/unit/strata/test_waive.py
- docs/strata/waive.md
- docs/strata/reliability.md
- tickets/T-1957/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_backpressure.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_circuit_breaker.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_clock_ordering.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_delivery_semantics.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_distributed_txn.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_fallback.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_interactive_cost.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_message_schema.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_observability.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_process_bounds.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_retry.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_shared_state.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_slo.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_spof.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_ssot.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_starvation.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_supply_chain_boot.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_sync_depth.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_txn.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_waive.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_waive.py
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/waive.md
  reason: narrow package glob to the 21 call sites + shared helper + its test the
    ticket actually touches
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/reliability.md
  reason: AFFECT001 closure target for all 20 check_X_obligations touched by the shared
    helper extraction
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1957/**
  reason: residue ticket filed by T-1938 for the DUP001 region_kernel finding
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_builds_one_violation_per_stale_waiver
- tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_uses_stale_detail_message
- tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_empty_stale_yields_empty_tuple
- tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_factory_lambda_can_add_extra_fields
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