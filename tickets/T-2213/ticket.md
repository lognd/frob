---
id: T-2213
title: ticket_readiness has grown to 80 lines (ARCH001) and lost its frob:doc edge
  (COV001) after seven separate lands into scripts/fleet_status.py in one day
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/system/test_fleet_status_ticket_readiness_arch001.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_fleet_status_ticket_readiness_arch001.py
  reason: new repro/regression test
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'doc closure: ticket_readiness''s split-off predicates need their own frob:doc
    anchors in this file'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
designated_repro_test: tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
acceptance:
- text: 'Measured: scripts/fleet_status.py:351 ticket_readiness is 80 lines (ARCH001
    threshold 60) and public with no frob:doc edge (COV001). The file is now 1383
    lines after SEVEN lands today -- T-2133, T-2172, T-2179, T-2180, T-2181, T-2182,
    T-2196 -- each adding a capability the coordinator asked for. No single land was
    unreasonable; the accumulation is. This test MUST fail against current main.'
  evidence:
  - tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
- text: 'Split ticket_readiness along the questions it answers, which are already
    distinct and separately printed: does the ticket exist on main, is it leased,
    does the live lease scope diverge from the declared scope, is it blocked_by something,
    has a branch already implemented it. Each is an independent predicate feeding
    one verdict. Do NOT split on line count to get under 60 -- that produces arbitrary
    halves that must both be read to understand either, and the next capability re-trips
    it. Restore the frob:doc edge to the real anchor in docs/guides/coordinator-scripts.md
    rather than adding a token anchor to silence COV001.'
  evidence:
  - tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 59fd9c6cb27cf70c7856e94256b98cd7fd1c6919
---
