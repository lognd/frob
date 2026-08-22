## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_land_proof_state_ok (new, T-2129) --
  single terminal-state allowlist for LAND-PROOF verification (done/dropped,
  anchor-left-queued/blocked, and now a queued ticket with a recorded
  `## Failure log`).
- src/frob/app/ticket_runner/_land_cmd.py::_land_proof_checks -- now returns
  `state_ok` (via `_land_proof_state_ok`) instead of the raw `is_anchor` bit,
  so both callers stop independently re-deriving the same allowlist condition.
- src/frob/app/ticket_runner/_land_cmd.py::_print_land_proof -- consumes the
  shared `state_ok` directly; behavior unchanged for done/dropped/anchor
  shapes, now also correctly reports `verified=True` for the queued-with-
  failure-log shape T-2109's land hit.
- src/frob/app/ticket_runner/_land_cmd.py::_report_stale_post_land_verify_markers
  -- same consolidation, same new allowlist entry.
- src/frob/app/ticket_runner/_land_cmd.py::_finish_land_after_success -- the
  ERROR line printed on an unverified proof no longer asserts a blanket "did
  NOT reach main (or state not terminal)" every time; it re-derives which of
  the two checks actually failed (via `_land_proof_checks`, read-only) and
  names that one, so it can never contradict the `LAND-PROOF:` line's own
  `is_ancestor_of_main` field printed immediately above it.

Evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log
  -- bound to acceptance [0], designated as BUG002 repro via
  `--designate-repro --base-ref df2534533` (the commit that carries the
  test alone, before the fix): confirmed FAILED_AT_PARENT (genuine repro).
  Manually re-confirmed by hand at df2534533 too (both AttributeError
  pre-fix-of-the-fix-commit, and a real assertion failure once that was
  patched), via a detached `git worktree add` checkout run against this
  worktree's own `.venv/bin/python -m pytest` -- 1 failed. Post-fix: 1
  passed (`uv run pytest tests/test_ticket_work_and_land_finish.py::
  TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_
  recorded_failure_log -o addopts="" -q` -> `1 passed`).
- Full `TestLandProofAndFinish` class: 6 passed, 5 pre-existing failures
  unrelated to this ticket (see Filed below) -- same 5 fail identically
  with T-2129's own changes reverted, confirming they predate this ticket.
- `uv run frob check --land-parity`: clean -- 0 unscoped errors.
- `uv run frob check --only scope --only tickets --ticket T-2129`: 1 error
  (gate:TICK TICK004 on T-0969, an unrelated pre-existing rotting-ticket
  finding, confirmed present in tickets.md independent of this ticket's
  scope) -- gate:SCOPE clean after narrowing scope to
  src/frob/app/ticket_runner/_land_cmd.py, tests/test_ticket_work_and_land_finish.py,
  and tickets/T-2167/**.

Filed: T-2167 (residue, bug) -- 5 pre-existing
`TestLandProofAndFinish` fixtures construct a fake `LandReport` via
`SimpleNamespace(final_id=tid, commit_sha=commit_sha)` with no `ticket_id`,
which T-2091's `_print_land_proof` now reads
(`_LAST_CLAIMS_OUTCOME.pop(report.ticket_id, ...)`), raising
`AttributeError` instead of testing what they were written to test.
Confirmed present on `main` directly, not a worktree artifact. Out of
scope for T-2129 (this ticket's scope is the LAND-PROOF message-
consistency fix, not this pre-existing fixture drift).

Gates: `frob check --land-parity` clean; `frob check --only scope --only
tickets --ticket T-2129` shows only the unrelated pre-existing TICK004
finding (no waiver needed -- not this ticket's scope, not a new finding).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 111 +++++++++++++++++++++---------
 tests/test_ticket_work_and_land_finish.py |  39 +++++++++++
 tickets/T-2129/ticket.md                  |  38 ++++++++--
 tickets/T-2167/ticket.md        |  63 +++++++++++++++++
 4 files changed, 213 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: SELFAUDIT001@design, TICK004@tickets.md
