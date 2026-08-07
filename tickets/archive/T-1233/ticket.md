---
id: T-1233
title: 'fix campaign: land every confirmed class-A+class-B finding in the 2026-07-29
  staleness sweep'
state: done
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- docs/commands/**
- docs/guides/**
- docs/modules/**
- docs/strata/**
- docs/*.md
- FROBLEMS.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:uv run frob check --only docanchor --only docblocks exit=0 sha256=d1e1254bdf68
designated_repro_test: null
threat: null
component: null
---
Fix every confirmed class-A + class-B finding in docs/audits/docs-staleness-2026-07-29.md, organized to land in a few batches: commands/, guides/, modules/, strata/, top-level. Acceptance: every finding line in the audit doc either fixed or explicitly re-verified-as-correct, and the two class-A warnings (docanchor/docblocks DOC006, DOC004) clear. Independent of the mechanism tickets -- content fixes need no new gates.