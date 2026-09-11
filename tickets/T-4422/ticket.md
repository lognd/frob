---
id: T-4422
title: Migrate docs prose off ticket citations into the ledger (DOC012)
state: queued
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: T-2994
tier: story
sprint: v0.533.0
runs_last: false
milestone: 0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a full frob check on docs/, when DOC012 is measured, then its finding
    count is 0
  evidence: []
- text: Given a grep for ticket-id citations in docs/ prose, when counted, then the
    file count is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOC012 measured 48 findings on a full check today (2026-09-11); separately, 140 docs/ files still cite tickets in prose (T-3022's own denominator). Move that narrative into the ticket ledger and leave docs describing current behavior only. Denominators: 48 (DOC012), 140 files (prose citations, T-3022).