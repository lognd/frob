---
id: T-2129
title: LAND-PROOF reports verified=SKIPPED-UNMEASURED/ERROR for a successful QUEUED-with-failure-log
  land (is_ancestor_of_main=True contradicts its own ERROR)
state: done
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- tickets/T-2167/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: narrow to LAND-PROOF error-message consistency fix
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: narrow to LAND-PROOF error-message consistency fix
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: narrow to LAND-PROOF error-message consistency fix
  actor: logan
  at: '2026-08-11'
- op: remove
  glob: src/frob/app/ticket_runner/**
  reason: narrow to the two touched files only
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2167/**
  reason: residue ticket filed from this worktree
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log
acceptance:
- text: Given a QUEUED ticket with a recorded failure log landed via frob ticket land
    (publishing the failure log to main, no done transition), when the LAND-PROOF
    self-check runs, then it reports verified=True (or an equivalently non-error terminal
    outcome) instead of an ERROR that contradicts its own printed is_ancestor_of_main=True
    field
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket land T-2109` (a QUEUED ticket with a recorded failure log,
never DONE -- `frob ticket fail` requeues rather than closing) actually
published its content to main correctly: commit
`0106ba15d9b3e64d19a866dcff2f6a3b9802230d`, confirmed both required
ways --

  git merge-base --is-ancestor 0106ba15d9b3e64d19a866dcff2f6a3b9802230d main
  # exits 0, real ancestor

  git show --stat 0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  # 3 files, includes tickets/T-2109/ticket.md with the Failure log section

  python3 scripts/verify_lands.py 0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  # ON HEAD

But `frob ticket land`'s own end-of-run self-check printed:

  LAND-PROOF: ticket=T-2109 commit=0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  is_ancestor_of_main=True state_on_main=queued
  claims_reverify=skipped-unmeasured verified=SKIPPED-UNMEASURED
  ERROR: ticket land: T-2109 LAND-PROOF did not verify -- the commit
  ... did NOT reach `main` (or the ticket's on-main state is not
  terminal); treat this land as FAILED despite the 'landed as' line
  above ...

`is_ancestor_of_main=True` on the SAME line the ERROR message claims
"did NOT reach main" -- the self-check's own printed fields already
contradict its own conclusion. The real defect: for the QUEUED-with-
failure-log shape (T-2109's own new code path, printed one line
earlier: "T-2109 is QUEUED with a recorded failure log, not landing a
done ticket -- publishing the failure log to main as-is, no done
transition attempted"), the LAND-PROOF verifier's terminal-state
allowlist evidently does not include `queued` as an acceptable
post-fail state, so a genuinely successful publish is reported as a
failed one. An operator trusting the ERROR line alone (rather than
manually re-deriving ancestor-of-main and diffing content, exactly as
this ticket's own error message tells them to) would wrongly believe
the fail record never reached main and could re-attempt or
hand-recover a commit that was already there.

Likely fix location: whatever function computes `verified=` from
`is_ancestor_of_main`/`state_on_main` needs to treat `queued`
(specifically: queued WITH a non-empty failure log, the exact shape
`frob ticket fail` produces) as an acceptable terminal state for this
one land shape, alongside whatever states already pass (`done`,
presumably `dropped`/`blocked`). Scope not identified precisely --
whichever module owns the post-land verification message quoted above
(printed by the `frob ticket land` CLI path, likely in
`src/frob/app/ticket_runner/` or `src/frob/tickets/_land*.py`).

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
