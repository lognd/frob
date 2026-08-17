---
id: T-2167
title: 5 TestLandProofAndFinish fixtures raise AttributeError on report.ticket_id
  (T-2091 regression)
state: done
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
evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_an_anchor_ticket_left_queued_on_main
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_still_refuses_a_non_anchor_ticket_left_queued
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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

## Done report

Diagnosis: the AttributeError is a stale-fixture defect, not a production
bug. `LandReport.ticket_id: str` (src/frob/tickets/_models.py:2337) is a
REQUIRED field on every real land report; `_print_land_proof`'s read of
`report.ticket_id` (src/frob/app/ticket_runner/_land_cmd.py:1319) is
T-2091's intentional lookup into `_LAST_CLAIMS_OUTCOME`. The five failing
tests built `SimpleNamespace(final_id=..., commit_sha=...)` fakes with no
`ticket_id` -- confirmed by reproducing the AttributeError against `main`
HEAD directly (`git show main:tests/test_ticket_work_and_land_finish.py`)
before making any change: `5 failed, 6 passed`.

Fix: added `ticket_id=tid` (or the ticket id already in scope,
`real_report.final_id`) to each of the five `SimpleNamespace(...)`
constructions, matching the pattern T-2129's own fixture already used.
Two of the five tests also asserted the OLD LAND-PROOF wording
(`verified=True` / `verified=False`); once given a valid `ticket_id`,
their real `_LAST_CLAIMS_OUTCOME` lookup legitimately resolves to
SKIPPED_UNMEASURED (their Done reports carry no "### Captured claims"
section -- confirmed by reading `_reverify_done_report_claims_post_merge`,
src/frob/tickets/_land_verify.py, and tracing the `claims is None` path
both fixtures hit), so per T-2091's deliberate three-state contract the
printed token is correctly `SKIPPED-UNMEASURED`, never a boolean spelling.
Updated those two assertions to check the new contract's actual output
while preserving each test's real underlying property:
`test_cli_land_invoked_with_root_equal_to_worktree_still_verifies` still
asserts `is_ancestor_of_main=True` (the property under test);
`test_unverified_land_exits_nonzero_even_without_finish` still asserts
`is_ancestor_of_main=False` and the `exc_info.value.code != 0` SystemExit
(the RETURNED verified bool is unaffected by the skip -- only the
PRINTED token changes, per `_print_land_proof`'s own docstring).

No production code was touched. No `try/except`/`getattr` fallback was
added. No test was deleted or skipped.

Changed:
tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_cli_land_invoked_with_root_equal_to_worktree_still_verifies
tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_verifies_an_anchor_ticket_left_queued_on_main
tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_still_refuses_a_non_anchor_ticket_left_queued
tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_retire_on_proof_refuses_and_touches_nothing_when_unverified
tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_unverified_land_exits_nonzero_even_without_finish

Evidence:
- Repro against pre-fix main: `uv run pytest tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish -o addopts="" -q` -> `5 failed, 6 passed`.
- Post-fix, targeted class: `uv run pytest tests/test_ticket_work_and_land_finish.py -k TestLandProofAndFinish -o addopts="" -q` -> `11 passed, 43 deselected in 10.49s`.
- Whole file: `uv run pytest tests/test_ticket_work_and_land_finish.py -o addopts="" -q` -> `54 passed in 17.42s` (collected count unchanged -- no test added or removed).
- `uv run frob check --land-parity` -> clean, 0 unscoped errors.
- `uv run frob check --ticket T-2167` -> no findings attributable to the changed lines (SCOPE002 warnings on unrelated tests in the same file are pre-existing; ARCH/DRIFT/PRE/SELFAUDIT/TEST/TICK errors are all repo-wide pre-existing findings in other files).
- `ruff format --check` flags this file both before and after the change (confirmed against main's own copy too) -- pre-existing repo-wide drift, tracked separately as T-1945, not introduced by this ticket.

Filed: none.

Note for the record: these five fixtures were independently confirmed
broken by three separate agents over several hours before this ticket was
worked, each correctly keeping the fix out of their own ticket's scope
and filing/flagging it instead. The system worked as designed, but it
also means a known-broken test class sat visible (not silently landing
bad tests, but not fixed either) for hours before someone picked it up --
worth noting as a backlog-latency data point, not a process failure.

Gates: `frob check --ticket T-2167` -- no errors traceable to this
ticket's changed lines (see Evidence above); `frob check --land-parity`
clean.

### Changed
```
 tickets/T-2167/ticket.md | 8 +++++++-
 1 file changed, 7 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_an_anchor_ticket_left_queued_on_main` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_still_refuses_a_non_anchor_ticket_left_queued` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/graph/callgraph.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST001@src/frob/graph/callgraph.py, TICK004@tickets.md
