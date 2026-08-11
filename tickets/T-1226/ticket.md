---
id: T-1226
title: 'docs integrity: close the silent-miss classes from the 2026-07-29 staleness
  sweep'
state: done
kind: docs
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- docs/audits/docs-staleness-2026-07-29.md
- tickets/T-2080/**
evidence_scope:
- tests/integration/test_interfaces.py
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
- op: remove
  glob: src/frob/graph/**
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_doclink.py
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_docanchor.py
  reason: 'narrow to the audit doc alone: this pass corrects the gate-gap-class status
    table against current main (5 of 6 classes shipped, catalogued and re-verified
    as wired not just present), no gate mechanism code touched this pass; those files
    also no longer exist under these names (merged into _doclink_docanchor.py)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2080/**
  reason: residue ticket filed by this ticket's own investigation pass, needed for
    the land's touched-set
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
121-doc staleness sweep (docs/audits/docs-staleness-2026-07-29.md): 2 class-A gate-flagged findings, ~140 class-B silent misses, 6 gate-gap classes, a drift-lock candidate list, and one code-side bug. Every silent miss indicts a frob gate gap: each gap class becomes a mechanism ticket, plus a fix campaign for the doc content itself.