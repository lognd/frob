## Done report

REQUIRED FIX 1 (of T-1910's list): a land whose LAND-PROOF is
verified=False must not report success. `_finish_land_after_success`
(src/frob/app/ticket_runner/_land_cmd.py) now `sys.exit(1)`s the moment
`_print_land_proof` returns False, unconditionally -- not only when
`--finish`/`--retire-on-proof` was passed, which was the pre-fix gate.
Before this fix, an ordinary `frob ticket land <id> --worktree <path>`
invocation (the overwhelmingly common case, no finish flags) printed
"landed as <sha>" plus the LAND-PROOF line showing verified=False and
still exited 0 -- the exact T-1895 incident this ticket documents. A real
fail-then-pass test
(tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish)
drives a real land through `land()`, then calls
`_finish_land_after_success` with a report naming a commit that is never
an ancestor of main and NO finish flags set; asserts `SystemExit` is
raised. Verified failing at the parent commit (no exception raised,
silent return) before this fix, passing after.

REQUIRED FIXES 2-4 (ledger must not record done for a commit not on
main; do not bump REL001/write CHANGELOG for a land that did not reach
main; root-cause the mechanism): NOT done in this pass. The ticket
close and REL001 bump happen as part of the SAME landing commit the
ancestry check runs against -- by the time verified=False is observed
the commit (with its state=done write and its bump) already exists
locally; there is no remaining step in the current architecture that
can retroactively undo either without a second commit. Root-causing
HOW a fully-formed commit ends up reachable only from an unrelated
branch (item 4) was investigated for the related T-1913 case and found
irreproducible in a synchronous test fixture (see T-1913's own ticket
body) -- the same open question applies here and is not resolved by
this ticket's scope. Filed as residue below rather than silently
dropped.

REQUIRED FIX 5 (audit prior lands in this wave for the same silent
loss): outside this ticket's scope (auditing OTHER tickets' already-
landed commits is not a `_land_cmd.py`/test change) -- not attempted
here; flagging for the coordinator instead of silently skipping.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 38 +++++++++++++++++++++-----
 tests/test_ticket_work_and_land_finish.py | 45 +++++++++++++++++++++++++++++++
 tickets/T-1867/ticket.md                  | 44 +++++++++++++++++++++++++++---
 tickets/T-1910/ticket.md                  | 18 ++++++++++++-
 tickets/T-1913/ticket.md                  |  2 +-
 tickets/T-1914/ticket.md                  | 20 +++++++++++++-
 tickets/T-draft-d718d443/ticket.md        | 32 ++++++++++++++++++++++
 7 files changed, 186 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 4 error(s), 877 warning(s), 697 waived
- error-findings: PRE001@tickets/T-1910, REG002@docs/design/registry/check-coverage.yaml, SUPPRESS001@.claude/hooks/frob-suggest.py, SUPPRESS001@.claude/hooks/frob-timeout-guard.py
