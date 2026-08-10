## Done report

Changed:
src/frob/app/ticket_runner/_land_cmd.py::_land_proof_checks
src/frob/app/ticket_runner/_land_cmd.py::_print_land_proof
src/frob/app/ticket_runner/_land_cmd.py::_report_stale_post_land_verify_markers
src/frob/app/ticket_runner/_land_cmd.py::_land (root resolution ordering)

Evidence: tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_an_anchor_ticket_left_queued_on_main, tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_still_refuses_a_non_anchor_ticket_left_queued, tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies. Full module: 44/44 pass, no regressions.

NOTE: this Done report is a RE-RECORD. My original close (commit
b3bf8a753) was silently dropped from the ledger -- the coordinator's own
`frob ticket land T-1903 --worktree <this worktree>` command internally
merges main INTO this worktree as one of its own steps, and that merge
brought main's still-`queued` copy of `tickets/T-1884/ticket.md`
(main had never seen my close) back over my local `done` edit with no
conflict reported (both a fast-forward-shaped change on an unrelated
file, from git's perspective). Re-recorded here entirely via the `frob
ticket` CLI, never by hand-editing the ledger.

PART 1 -- the ticket's ORIGINAL scope (anchor tickets), FIXED:
`_land_proof_checks` now also returns the loaded ticket's `anchor`
field; `_print_land_proof`'s `state_ok` accepts `queued`/`blocked` in
addition to `done`/`dropped` when `anchor` is True -- mirroring
`_skip_close_for_anchor_no_close_requested`'s (T-1874) own condition.
The sibling `_report_stale_post_land_verify_markers` call site gets the
identical anchor-aware `state_ok` so the two LAND-PROOF checks cannot
drift. Two regression tests: an anchor ticket left queued now reads
`verified=True` (the T-1820 shape); an ordinary ticket left queued
still reads `verified=False` (the carve-out is not a blanket
relaxation).

PART 2 -- the coordinator's ADDITIONAL MEASUREMENT (T-1895, a NON-anchor
false negative), PARTIALLY ADDRESSED, HONEST STATUS BELOW:

Found and fixed a real, separate, provable gap while investigating:
`_resolve_land_root`'s own docstring already claimed the CLI `_land`
wrapper resolves its own `root` local a SECOND time after `land()`
returns (needed because `_land_core_prepare`'s internal resolution is
local to that function and never propagates back out) -- but no such
call site actually existed anywhere in `_land_cmd.py`. Added it: `_land`
now resolves `root` once, up front, before calling `_land_core`, and
reuses that single resolved value for `_report_land_result`,
`_push_after_land`, and `_finish_land_after_success`'s
`_print_land_proof` call. Regression test
(`test_cli_land_invoked_with_root_equal_to_worktree_still_verifies`)
proves the wiring now matches the docstring's stated design.

HOWEVER -- I could NOT reproduce the T-1895 shape itself with this fix,
and want to say so plainly rather than claim it closed: `git worktree
add`-linked worktrees (the playbook's own standard, and almost
certainly what `--worktree .../t1895-t1893` was) share ONE common
`.git` dir and thus the SAME ref database -- `git -C <linked-worktree>
merge-base --is-ancestor <sha> main` sees the true, current `main` tip
synchronously regardless of which worktree the query runs from, so the
"querying the wrong checkout" theory does not, by itself, explain a
false negative in that topology. I deliberately reverted the root-
resolution fix and re-ran the same regression test -- it still passed,
confirming this locally. The real mechanism behind the T-1895
reproduction remains UNCONFIRMED.

Filed T-1913 ("LAND-PROOF is_ancestor_of_main=False for a
non-anchor ticket whose land fully succeeded (T-1895)") carrying the
full investigation notes and next-step directions (renumbers at land),
rather than have T-1884 claim to close over an unconfirmed fix, per the
coordinator's own instruction.

Filed: T-1913 (the T-1895 false-negative, unresolved).

Gates: `frob check --ticket T-1884 --only arch --only ty --only gates`
-- gate:ARCH 0 errors, gate:COV 0 errors. gate:SCOPE errors present are
pre-existing artifacts from T-1903/T-1907's own already-closed/landed
work committed earlier in this SAME series worktree (rapid-debt.jsonl,
tickets/T-1903/*.md, tickets/T-1907/*.md, src/frob/tickets/
_land_verify.py) -- diff noise from this scoped check comparing against
the worktree's stale original base, not a T-1884 defect. gate:REG 1
error is the same pre-existing SYS-IFACE-ORDER/SYS104 registry drift
already noted in T-1903's and T-1907's Done reports. The `ty`
diagnostics are the same pre-existing tests/unit/gates/test_sys_
interface_canonical_order.py argument-type mismatch, confirmed unrelated
by `uv run ty check` scoped to this ticket's exact touched files, which
reports "All checks passed!".

### Changed
```
 rapid-debt.jsonl                          |  1 +
 src/frob/app/ticket_runner/_land_cmd.py   | 30 +++++++++++
 tests/test_ticket_work_and_land_finish.py | 70 ++++++++++++++++++++++++++
 tickets/T-1884/ticket.md                  | 12 ++++-
 tickets/T-1913/ticket.md        | 82 +++++++++++++++++++++++++++++++
 5 files changed, 193 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 872 warning(s), 697 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml
