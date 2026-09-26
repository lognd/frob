---
id: T-draft-f9786f16
title: 'evidence: no sanctioned way to bind evidence for a pure .md change; add a
  doc-anchor evidence kind'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
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
- src/frob/tickets/_evidence.py
- src/frob/_cli_parsers/_ticket/_evidence.py
- src/frob/tickets/_land_verify.py
- tests/unit/tickets/test_doc_anchor_evidence.py
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-408: a ticket whose whole change is Markdown has no evidence kind except `cmd:` -- any node id is UnknownEvidence, so agents fabricate a command or the land refuses HollowDoneReport. Deliver: a `doc:` evidence kind (`frob ticket evidence <id> doc:docs/path.md#anchor`) that resolves when the anchor exists in the merged tree and the file is in the ticket's diff, re-verified at land like pytest ids; docs-kind rapid closes accept it as full evidence; positive control: a docs-only fixture ticket lands with `doc:` evidence and is refused when the anchor is missing.
