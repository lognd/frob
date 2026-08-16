---
id: T-2214
title: 'Nothing gates an oversized function at land time, so ARCH001 accumulates in
  exactly the files the fleet works most: 4 findings in _land_cmd.py, plus fleet_status.py,
  _new.py and telemetry.py'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Measured correlation between fleet activity and ARCH debt. ARCH001/ARCH103
    errors by file: src/frob/app/ticket_runner/_land_cmd.py 4, scripts/fleet_status.py
    1, src/frob/app/telemetry.py 1, src/frob/app/ticket_runner/_new.py 1. Lands touching
    those same files today: fleet_status.py 4, _land.py 3, _land_cmd.py 3, _new.py
    2. The debt concentrates exactly where the fleet works most -- no single land
    is unreasonable, the accumulation is. Concrete instance: scripts/fleet_status.py::ticket_readiness
    reached 80 lines (threshold 60) after seven separate lands in one day. This test
    MUST fail against current main.'
  evidence: []
- text: 'ARCH001 is a SIZE threshold, not a missing-directive family -- it cannot
    be expressed in T-2201''s _DOC_TEST_EDGE_FAMILIES (label, directive, waive_rule)
    shape, and T-2201''s author was right to parameterise the edge families and disclose
    ARCH as out of scope rather than force it in. This needs its own diff-scoped check:
    for each function the diff ADDS or MODIFIES, measure its post-diff length and
    decision count and refuse when the diff pushes it past threshold. Compare against
    the merge-base so a function already over threshold and merely touched is not
    blamed on this land.'
  evidence: []
- text: Do NOT reintroduce a full unscoped frob check at land time -- that is the
    ~208s cost T-1684 removed and T-2114/T-2201 correctly avoided by working from
    the diff alone. Do NOT refuse on a function that was ALREADY over threshold before
    the diff; that would block unrelated work in the busiest files and is exactly
    the global-vs-attributable mistake T-2198 just fixed for the TICK gate. Refuse
    only on what the landing diff itself made worse.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
