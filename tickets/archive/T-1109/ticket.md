---
id: T-1109
title: 'docs: DOC006 doc-pointer round-3 burn-down (~41 residual warnings after T-1015/T-1016)'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- CHANGELOG.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: tests/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: CHANGELOG.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tickets.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check WHEN the doc gate runs THEN DOC006 reports zero unwaived
    warnings, with every fixed pointer resolving to a real heading slug and no matcher
    loosening
  evidence:
  - cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
threat: null
component: null
---
T-1015 (matcher hardening, 771->133) and T-1016 (round 2) left ~41 DOC006 doc-pointer warnings. Round 3: fix or reasoned-waive every residual site. No matcher/threshold loosening; follow T-1015's FP-class analysis before touching the matcher. Narrow scope to the real finding sites at start.