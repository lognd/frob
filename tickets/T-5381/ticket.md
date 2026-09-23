---
id: T-5381
title: 'extending-guide anchor T-4118 fragment stale: frob.tickets._models.py cites
  a slug the guide no longer has'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- docs/guides/extending/failure-injection-acceptance-criteria.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1 fails -- src/frob/tickets/_models.py's DOC002 anchor cites fragment '#failure-injection-acceptance-criteria-name-every-field-t-4118' but docs/guides/extending/failure-injection-acceptance-criteria.md's current H1 slug is 'failure-injection-acceptance-criteria-name-every-field' (no trailing -t-4118). Either the guide's heading was renamed/retitled and the anchor needs updating, or the anchor's trailing ticket-id suffix is now stale. Not covered by any open ticket found.