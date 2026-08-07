---
id: T-0671
title: 'strata: bounded/staleness-gated assume+waiver mechanism - un-droppable floor
  view for conformance obligations'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0668
- T-0669
- T-0670
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view
- tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_missing_expiry_marker_treated_as_expired
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none
designated_repro_test: null
acceptance:
- text: Given a waiver older than its staleness bound, when checked, then it is treated
    as expired and the underlying obligation re-fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_expired_waiver_refires_and_is_flagged
- text: Given any active waiver, when frob check runs, then it appears in the floor
    view and cannot be hidden from default output
  evidence:
  - tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness::test_unexpired_waiver_still_visible_in_floor_view
threat: null
component: null
---
Closes acceptance-criterion (5): every conformance escape hatch (interface/purpose/binding waivers) must be bounded (expiry/staleness-gated) and surfaced in an un-droppable floor view so it cannot become a permanent silent exemption. Depends on the three conformance checks existing first since this wraps their waiver channel.