---
id: T-1158
title: 'strata: declare real owns= paths on tickets_ledger''s five writers to drop
  the SYS205:tickets_ledger waivers'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1164
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
T-1146 wired module= into the live SELFAUDIT001/frob sys audit call
sites, so SYS203's arbiter-awareness (T-1025) and SYS201's (T-1149) now
genuinely discharge tickets_ledger's five writers live -- the five
SYS203:tickets_ledger waivers in design/frob.strata were dropped as part
of that land (verified stale via frob sys audit's own detection).

The five SYS205:tickets_ledger waivers remain: SYS205's WRITE mode
path-scoping (T-1060) still fires because none of the five nodes
(cli/gates/fleet/core/serve) declare an owns/acl path claim at all.
Declaring a real owns="tickets.md" (or similar) on each would need:
1. Verification that SYS201 genuinely stays clean for the resulting
   overlapping owns claims now that it is arbiter-aware (should, per
   T-1149, but not verified end-to-end against the real design file).
2. Verification against SYS205's OWN "write_outside_declared_path"
   check: the literal write-target paths SYS205 extracts from each
   node's actual bound code must overlap whatever owns= path is
   declared, or a NEW SYS205 finding fires instead of the current
   no_declared_path one.

This ticket is that verification + the owns= declarations themselves,
so the five SYS205:tickets_ledger waivers can finally be dropped too.