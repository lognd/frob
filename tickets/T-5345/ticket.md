---
id: T-5345
title: Bulk-remove T-#### prose citations from docs/modules and docs/strata (T-5134
  follow-up)
state: queued
kind: docs
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/*.md
- docs/strata/*.md
- docs/guides/*.md
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
found while working T-5134: scripts/count_ticket_citations.py --scope docs measured 7215 remaining T-#### prose citations after T-5134's own pass (which cleaned the 24 files that each carried exactly one bare citation). The bulk lives in large modules/strata/guides docs (docs/modules/gates.md alone: 1279) where citations are woven into gate-history narrative prose, not simple asides -- removing them safely needs a slower, section-by-section pass (or a decision to leave narrative-history sections as a declared exemption alongside docs/audits and docs/design/registry), out of scope for T-5134's own budget. Re-run scripts/count_ticket_citations.py --scope docs --list to reproduce the current list.