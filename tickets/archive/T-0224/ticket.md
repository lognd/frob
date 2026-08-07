---
id: T-0224
title: frob sys doc matrix prints PROVED (L4) for claims that were only ASSUMED
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_assumed_discharge_renders_distinct_from_proved
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_discharged_obligation_renders_proved
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 9 (medium, overstates assurance): audit summary says {proved: N, assumed: M} but the matrix rows for assumed CWE discharges read PROVED (L4). Add a distinct ASSUMED status in the matrix rendering; a claim resting on an assume must never print as PROVED. Regression fixture: model with one proved and one assumed claim, assert distinct labels.