---
id: T-1149
title: 'strata: SYS201 gains arbiter-awareness (or a first-class shared-path concept)
  so SYS205 WRITE path-scoping can discharge without regressing SYS201'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_contention.py
- tests/unit/strata/test_contention.py
- design/frob.strata
- docs/strata/host.md
- tests/unit/strata/litmus/contention_path_arbitered.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/litmus/contention_path_arbitered.strata
  reason: T-1149's own new SYS201 arbiter-aware litmus fixture
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_common_arbitered_resource_discharges
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_common_arbitered_resource_still_fires_without_module
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_unarbitered_overlap_still_fires_with_module
- tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires
designated_repro_test: null
threat: null
component: null
---
T-1061 wired SYS205 (mode-conformance) live into SELFAUDIT001/frob sys
audit, which surfaced a genuine new finding on frob's own design/
frob.strata: the five tickets_ledger write-mode accessors (cli/gates/
fleet/core/serve) declare no owns/acl path claim, tripping SYS205's
no_declared_path category (T-1060).

Declaring a synthetic owns="tickets.md" path on each of the five nodes
to discharge that finding was tried and rejected after measuring the
real consequence: it creates 20 NEW SYS201 (overlapping path claim,
_contention.py) findings across the five writers, verified directly by
calling check_resource_contention against the modified design file --
SYS201 has no arbiter-awareness at all, unlike SYS203 (which T-1025
taught to consult a resource's declared arbiter and discharge cleanly
for this exact tickets_ledger case).

This ticket is that same fix, applied to SYS201: either
1. Teach SYS201 (or a narrower successor rule) to consult a resource's
   declared arbiter the same way SYS203 (T-1025) and SYS204 already do,
   so N nodes legitimately sharing one arbitered path/resource (like
   tickets_ledger's five writers, all coordinating through the SAME
   `.frob/tickets.lock` flock, T-0458/T-0633/T-0956) stop being flagged
   as an overlapping-path conflict, OR
2. Build a first-class "declared shared write path" concept (a
   `resource`-like construct for filesystem paths, not just SYS203's
   store/SYS204's resource ids) that SYS201 and SYS205's WRITE
   path-scoping (T-1060) can BOTH consult, so a node can declare "I own
   this shared path, coordinated through arbiter X" once and have every
   relevant rule respect it.

Once either lands, design/frob.strata's five
`waive "SYS205:tickets_ledger" ...` clauses (added by T-1061, currently
the only way to keep SYS205 clean for these five nodes) can be dropped
in favor of a real owns= declaration that discharges SYS205 without
regressing SYS201.

Filed at T-1061's own close (LiveTrackerCited refusal -- the five
waivers above cite T-1061 as their live tracker; re-pointed to this
ticket's id so T-1061 itself can close).