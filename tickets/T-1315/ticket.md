---
id: T-1315
title: 'TEST005 floor ratchet-up schedule: 75/70 is a waypoint, not a surrender'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: low
parent: T-1273
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a package that has reached zero TEST005 findings at 75/70 WHEN the ratchet
    schedule lands THEN that package's effective floor is documented to step toward
    90/85 (per-package override or schedule), not remain frozen at the recalibrated
    minimum
  evidence: []
- text: GIVEN frob.toml's existing recalibration rationale comment WHEN the ratchet
    design is written THEN it explicitly cites and extends that rationale rather than
    contradicting or duplicating it
  evidence: []
threat: null
component: null
---
frob.toml [testing] recalibrated unit_branch_cov=75 / module_line_cov=70
on honest TEST005 attribution data (T-1235 fixed subprocess + pool-worker
coverage recording); the in-file rationale comment documents why these
specific numbers were chosen as the current floor, not a permanent
target.

Design a ratchet schedule: once a package (T-1276..T-1313 in this epic)
reaches zero TEST005 findings at 75/70, its floor should step up toward
90/85 rather than stay parked at the recalibrated minimum -- otherwise
the recalibration silently becomes a ceiling. Decide and document
(either in frob.toml as per-package floor overrides, or as a documented
schedule/policy the gate reads) how and when a cleared package's floor
increases, and how regressions below the new floor are caught.