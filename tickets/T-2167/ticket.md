---
id: T-2167
title: 5 TestLandProofAndFinish fixtures raise AttributeError on report.ticket_id
  (T-2091 regression)
state: queued
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-2129 (LAND-PROOF error-message consistency fix).

`tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish` has 5
tests that construct a fake land report via
`SimpleNamespace(final_id=tid, commit_sha=commit_sha)` (no `ticket_id`
field) and pass it to `_print_land_proof`:

- `test_cli_land_invoked_with_root_equal_to_worktree_still_verifies`
- `test_proof_verifies_an_anchor_ticket_left_queued_on_main`
- `test_proof_still_refuses_a_non_anchor_ticket_left_queued`
- `test_retire_on_proof_refuses_and_touches_nothing_when_unverified`
- `test_unverified_land_exits_nonzero_even_without_finish`

T-2091 added `_print_land_proof`'s own
`_LAST_CLAIMS_OUTCOME.pop(report.ticket_id, None)` read
(`src/frob/app/ticket_runner/_land_cmd.py`), which every real
`LandReport` satisfies (`ticket_id` is a required field,
`src/frob/tickets/_models.py::LandReport`) but these five fixtures do
not -- each now raises `AttributeError: 'types.SimpleNamespace' object
has no attribute 'ticket_id'` instead of testing what it was written to
test. Confirmed on `main` directly (not a worktree artifact):
`git show main:tests/test_ticket_work_and_land_finish.py` already
contains the same `SimpleNamespace(final_id=tid, commit_sha=commit_sha)`
shape.

Measured:
```
uv run pytest tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish -o addopts="" -q
5 failed, 6 passed
```
(the 6th newly-passing test is T-2129's own repro, added with a
corrected fixture that includes `ticket_id`).

Fix: add `ticket_id=tid` (or `ticket_id=real_report.final_id` where the
fixture already has a real id in scope) to each of the five
`SimpleNamespace(...)` constructions so they satisfy `_print_land_proof`'s
real read again, matching the pattern T-2129's own new test already
uses. Out of scope for T-2129 (that ticket's scope is narrowly the
`_land_cmd.py` LAND-PROOF message-consistency fix, not this pre-existing
fixture drift).
