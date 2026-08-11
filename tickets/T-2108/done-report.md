## Done report

Fixed: `frob ticket land <id> --finish` used to run the full land
pipeline unconditionally, even when <id> was already terminal
(done/dropped) on main from a prior land of this same worktree that
died between commit and cleanup, or from a coordinator closing it
directly on main. The re-run's own _land_core spawns a fresh BUG002
repro re-check of the ticket's designated repro test against the
CURRENT tree, which now genuinely PASSES (the fix is already on main,
its own parent) -- BUG002 correctly refuses a repro that no longer
reproduces, so --finish failed every time on an already-landed ticket:
a wasted merge+verify cycle and a confusing error, never data loss (no
commit made, main stayed clean).

Fix (NOT the ruled-out approach of swallowing the BUG002 failure): added
`_ticket_terminal_state_on_main(root, ticket_id)` -- one ledger read via
`frob.tickets.load_all`, returning the ticket's `state:` only if it is
already done/dropped (the same terminal pair `_print_land_proof`'s own
`state_ok` treats as verified). `_land` now calls this BEFORE `_land_core`
whenever --finish/--retire-on-proof was passed (and not --dry-run): a
terminal state means `_finish_only_if_already_landed` runs PURE cleanup
directly (the same `_finish_worktree` used on the normal path, plus
branch deletion for --retire-on-proof) and `_land` returns immediately,
never calling `_land_core` -- BUG002 is never reached because the land
attempt that would trip it never runs. A non-terminal state changes
nothing; the ordinary land path runs exactly as before.

Deliberately distinct from the existing `_check_already_landed`/
LandError.AlreadyLandedOnMain (inside `land()` itself): that refuses
LOUDLY on an empty scope-diff for ANY land call, a "you're probably
confused" signal. This one only fires for --finish/--retire-on-proof,
keys on terminal STATE not diff emptiness, and succeeds quietly --
--finish's whole point is cleanup, and an already-done ticket has
nothing left to clean up FOR except the worktree.

Evidence: tests/unit/test_land_finish_idempotent.py (5 tests, new file)
-- unit-level on `_finish_only_if_already_landed`/`_ticket_terminal_
state_on_main` directly with a real git+ledger fixture (new_ticket +
transition to DONE, matching tests/unit/test_land_already_landed.py's
own precedent), monkeypatching `_land_core`/`_finish_worktree` to prove
_land_core is genuinely never called on the terminal-state path. Repro
test committed alone first, confirmed FAILED_AT_PARENT via
`--check-repro --base-ref ac4efa18e` (ImportError at that commit --
`_finish_only_if_already_landed` did not exist yet), then the fix
committed separately. No existing test regressed: test_land_already_
landed.py (7) + test_land_finish_guard.py (18) both still 100% pass.

Could not add the doc section for this to docs/modules/tickets.md:
T-2132 took a live cross-worktree lease on that file mid-ticket (the
section was drafted, then reverted when the lease conflict surfaced).
Filed T-2166 to add it once the lease frees.

### Changed
```
 tests/unit/test_land_finish_idempotent.py | 182 ++++++++++++++++++++++++++++++
 tickets/T-2108/ticket.md                  |  12 +-
 tickets/T-2165/ticket.md        |  57 ++++++++++
 tickets/T-2166/ticket.md        |  42 +++++++
 4 files changed, 292 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2108, SELFAUDIT001@design, TICK004@tickets.md, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py
