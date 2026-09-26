---
id: T-draft-d042dc82
title: 'evidence: a bare test-file id resolves in matches_collected when at least
  one case from that file was collected and binds every case'
state: queued
kind: bug
origin: human
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/tickets/_models.py
- tests/unit/tickets/test_evidence_file_ids.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-6545 (logand.app-v2 F-410 follow-on, item 6 of the peer coordinator report): a bare file id (e.g. frontend/tests/unit/App.test.tsx) resolves in matches_collected (src/frob/tickets/_models.py ~1006-1019) as soon as at least one case from that file was collected, binding every case in the file to the evidence rather than just the one that ran. Deliver: bare-file-id binding should require either an explicit file-level evidence declaration or verification that all collected cases from that file are covered, with a positive control that a bare file id binds all its cases only when that is the intended (file-level) evidence shape, documented in docs/modules/tickets-lifecycle.md as the file-level workaround for consumers (e.g. logand.app-v2) that cannot yet emit per-case ids.