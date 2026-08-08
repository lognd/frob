---
id: T-1837
title: 'Unowned residue: src/frob/registry/_staleness.py E501/COV001/TEST001 from
  T-1264'
state: in-progress
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/registry/_staleness.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: doc anchors for the three residue COV001 fixes
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
---
Main's error floor is red at 13; six of those are unowned residue from
T-1264's land (the fixability registry field) in
`src/frob/registry/_staleness.py`, not covered by the existing residue
ticket T-1828 (scoped to `_query.py`/`_doable.py` only):

    E501     src/frob/registry/_staleness.py:59
    COV001   src/frob/registry/_staleness.py:62, 84, 192   (public symbols with no frob:doc edge)
    TEST001  src/frob/registry/_staleness.py:62, 84

Fixes are mechanical: add `frob:doc` edges for the three public symbols
(`missing_gate_rule_ids`, `sync_gate_rule_entries`,
`sync_gate_rule_fixability`), bind unit tests for the two TEST001
findings, and fix the long line (E501, line 59).
