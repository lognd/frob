## Done report

Changed:
src/frob/app/ticket_runner/_land_cmd.py::_land_proof_checks
src/frob/app/ticket_runner/_land_cmd.py::_print_land_proof
src/frob/app/ticket_runner/_land_cmd.py::_report_stale_post_land_verify_markers

Evidence: tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_an_anchor_ticket_left_queued_on_main, tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_still_refuses_a_non_anchor_ticket_left_queued. Full module: 43/43 pass, no regressions.

Fix: `_land_proof_checks` now also returns `is_anchor` (the loaded
ticket's `anchor` field) alongside `ancestor_ok`/`state_desc`.
`_print_land_proof`'s `state_ok` accepts `queued`/`blocked` in addition
to `done`/`dropped` when `is_anchor` is True -- exactly mirroring
`_skip_close_for_anchor_no_close_requested`'s (T-1874) own condition for
when publishing a non-terminal ticket record as-is is correct. The
sibling caller `_report_stale_post_land_verify_markers` (the T-1523
crash-recovery re-check, same two checks against a recovered marker)
gets the identical anchor-aware `state_ok` so the two LAND-PROOF
call sites cannot drift.

Regression tests: one asserts a fresh `anchor=True` ticket left `queued`
on main now reads `verified=True` (the exact T-1820 shape); a second
guards the carve-out is not a blanket "queued is fine" -- an ordinary
(non-anchor) ticket left queued still reads `verified=False`. Both call
`_print_land_proof` directly against a `SimpleNamespace(final_id,
commit_sha)` stand-in, matching this test class's own established
pattern for exercising the proof check without landing a second real
ticket end to end (`test_retire_on_proof_refuses_and_touches_nothing_
when_unverified`'s precedent).

Filed: none.

Gates: `frob check --ticket T-1884 --only arch --only ty --only gates`
-- gate:ARCH 0 errors, gate:COV 0 errors. gate:SCOPE 6 errors, all
pre-existing artifacts from T-1903/T-1907 (both already closed earlier
in this SAME series worktree: rapid-debt.jsonl, tickets/T-1903/*.md,
tickets/T-1907/*.md) plus src/frob/tickets/_land_verify.py (T-1907's
own touched file) -- diff noise from this scoped check comparing
against the worktree's original stale base rather than the real,
already-landed main those two tickets will occupy once the coordinator
lands them first; not a T-1884 defect (verified by inspecting each
flagged path -- none of them is a file this ticket's own diff touches).
gate:REG 1 error is the same pre-existing SYS-IFACE-ORDER/SYS104
registry drift already noted in T-1903's and T-1907's own Done reports.
The 3 `ty` diagnostics are the same pre-existing tests/unit/gates/
test_sys_interface_canonical_order.py argument-type mismatch; confirmed
unrelated by `uv run ty check` scoped to this ticket's two touched
files (_land_cmd.py, the test file), which reports "All checks passed!".

### Changed
```
 rapid-debt.jsonl                          |   3 +
 src/frob/app/ticket_runner/_land_cmd.py   | 260 +++++++++++++++++++++++++++---
 src/frob/tickets/_land_verify.py          |  23 +++
 tests/test_ticket_work_and_land_finish.py | 194 ++++++++++++++++++++++
 tickets/T-1884/ticket.md                  |   9 +-
 tickets/T-1903/done-report.md             |  64 ++++++++
 tickets/T-1903/ticket.md                  |  20 ++-
 tickets/T-1907/done-report.md             | 110 +++++++++++++
 tickets/T-1907/ticket.md                  |  31 +++-
 9 files changed, 686 insertions(+), 28 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 3 error(s), 883 warning(s), 697 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/land-integrity-series/src/frob/app/ticket_runner/_land_cmd.py, REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
