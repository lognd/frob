---
id: T-2531
title: 'post-land sweep regression from T-2503: E501/F401 residue (3 files, unrelated
  to T-2526''s F811)'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/graph/summary.py
- src/frob/testing/_collect_kotlin.py
- tests/unit/test_ticket_runner_repro_merge_base.py
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
Split off T-2526's other 4 (rule, file) identities so T-2526 can stay
scoped to just its F811 finding (a different root cause -- a lint
false-positive on a pytest fixture import -- from these, which are all
genuine long-line/unused-import findings verified live via a direct
`ruff check` run just now):

- E501  scripts/fleet_status.py:65
- E501  src/frob/graph/summary.py (line TBD, verify fresh)
- E501  src/frob/testing/_collect_kotlin.py:121
- F401  tests/unit/test_ticket_runner_repro_merge_base.py:20 (typani.Ok imported but unused)

All 4 confirmed live via a direct `ruff check` against the current
tree (not stale sweep residue). Mechanical fixes: shorten/wrap the 3
long lines, remove the unused import (ruff --fix handles the F401
one automatically). No functional risk.
