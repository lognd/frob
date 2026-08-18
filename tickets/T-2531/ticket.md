---
id: T-2531
title: 'post-land sweep regression from T-2503: E501/F401 residue (3 files, unrelated
  to T-2526''s F811)'
state: done
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
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): Pure lint/style fix (E501 line wraps in fleet_status.py/summary.py/_collect_kotlin.py,
    unused-import removal in a test file) -- no functional/behavioral change, only
    formatting and a dead import. All 4 findings were confirmed live via a direct
    ruff check before fixing; ruff check + ruff format --check are now clean on the
    touched files, and the touched test file''s own suite (7 tests) still passes.'
  actor: logan
  at: '2026-08-18'
  old_length: 782
  new_length: 1217
evidence:
- tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_no_warning_when_base_ref_already_matches
- tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_warns_when_base_ref_is_not_an_ancestor
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e2a976b4cf407c1f67d5a33f0047dc2e15cc79e9
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


frob:no-behavior-change reason="Pure lint/style fix (E501 line wraps in fleet_status.py/summary.py/_collect_kotlin.py, unused-import removal in a test file) -- no functional/behavioral change, only formatting and a dead import. All 4 findings were confirmed live via a direct ruff check before fixing; ruff check + ruff format --check are now clean on the touched files, and the touched test file's own suite (7 tests) still passes."