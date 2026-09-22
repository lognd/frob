---
id: T-4645
title: Clean tests/ticket_land_suite docstrings of change-narrative (DOCARCH001)
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/ticket_land_suite/test_archive.py
- tests/ticket_land_suite/test_claim_close.py
- tests/ticket_land_suite/test_dirt_ownership.py
- tests/ticket_land_suite/test_draft.py
- tests/ticket_land_suite/test_land_core.py
- tests/ticket_land_suite/test_land_lock.py
- tests/ticket_land_suite/test_land_plan.py
- tests/ticket_land_suite/test_push.py
- tests/ticket_land_suite/test_release.py
- tests/ticket_land_suite/test_verify_reset.py
- tests/ticket_land_suite/test_waive_deletion.py
- tests/ticket_land_suite/test_wip.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: parent
  old_value: T-4420
  new_value: T-2994
  reason: T-4645 is the ticket_land_suite docstring rewrite carved out of T-2994's
    test-hygiene tree; T-4420 needs T-2994's descendants closed
  actor: logan
  at: '2026-09-21'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
acceptance:
- text: DOCARCH001 count for tests/ticket_land_suite's 12 scoped files is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4420 (Clean land and gates test-suite docstrings of
change-narrative, DOCARCH001). Measured 2026-09-19 via `frob check
--only docblocks --files tests/ticket_land_suite --base dev`: 42
DOCARCH001 findings across tests/ticket_land_suite (test_land_core.py 7,
test_ledger_splice.py 6, test_land_plan.py 5, test_verify_reset.py 3,
test_release.py 3, test_land_lock.py 3, test_draft.py 3,
test_dirt_ownership.py 3, test_archive.py 3, test_wip.py 2,
test_push.py 2, test_waive_deletion.py 1, test_claim_close.py 1).

test_ledger_splice.py (6 findings) is excluded from this ticket's scope
as filed -- check .git/frob-leases before adding it; add it to scope
once free if still leased when this is picked up.

Rewrite each flagged docstring to state WHAT the test verifies; move
narrative (what a prior attempt got wrong, which policy superseded
which) into the originating ticket's body via `frob ticket body
--append`, per docs/modules/docstrings.md's purpose test.
