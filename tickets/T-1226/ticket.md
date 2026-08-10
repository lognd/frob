---
id: T-1226
title: 'docs integrity: close the silent-miss classes from the 2026-07-29 staleness
  sweep'
state: queued
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/graph/**
- docs/audits/docs-staleness-2026-07-29.md
- src/frob/gates/_doclink.py
- src/frob/gates/_docanchor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docanchor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.