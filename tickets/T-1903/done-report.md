## Done report

Changed:
src/frob/app/ticket_runner/_land_cmd.py::_absorb_pre_land_fixes
src/frob/app/ticket_runner/_land_cmd.py::_assert_design_loads_pre_land

Evidence: tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land (new regression test), plus the existing tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand and TestAbsorbPreLandFixes suites (37/37 pass, no regressions).

Fix: `_assert_design_loads_pre_land` now takes a `stage` kwarg
("pre-tier-a" / "post-tier-a") and `_absorb_pre_land_fixes` calls it
TWICE -- once before `_tier_a_pre_land_step` (unchanged, catches
pre-existing corruption with a clearer message) and once immediately
after it (new -- this is the load-bearing call). A post-tier-a parse
failure still calls `sys.exit(1)` (refuses the land, does not warn) and
the error message explicitly says the Tier-A rewrite itself broke
design/frob.strata, distinct from the pre-existing-breakage message.

Audit of _absorb_pre_land_fixes for other guards sequenced before their
own mutation (required by the ticket): the function has exactly three
steps -- `_fmt_pre_land_step` (an auto-fix, not a guard), the (now
twice-called) `_assert_design_loads_pre_land` guard, and
`_tier_a_pre_land_step` (the mutation). No other read-only guard exists
in this function that runs before a mutation it is meant to cover.
`_worktree_natives_verifiably_healthy`, called inside
`_tier_a_pre_land_step`, is a preflight that decides whether to exclude
WAIVE004 from the batch -- it is not verifying the OUTCOME of a
mutation, so it is not an instance of this bug class. Finding: no other
instance found; T-1903's own guard was the only one.

Regression test: `test_a_tier_a_handler_that_corrupts_design_after_it_
was_healthy_refuses_the_land` monkeypatches
`frob.gates._fix_engine.apply_tier_a_fixes` to write unparseable
content into `design/*.strata` as its side effect (design root parses
cleanly before the call, matching T-1900's exact shape) and asserts
`_absorb_pre_land_fixes` raises `SystemExit(1)`.

Filed: none (this ticket's own fix covers the whole finding; the audit
found no other instance to spin off).

Gates: `frob check --ticket T-1903 --only ty --only gates` -- gate:COV
0 errors, gate:SCOPE 0 errors, gate:PRE 0 errors (after a
`frob ticket sweep T-1903` re-run following the scope extension). The
remaining 3 `ty` diagnostics and the `gate:REG` REG002/REG011 findings
are pre-existing, unrelated to this ticket (tests/unit/gates/test_sys_
interface_canonical_order.py's own argument-type mismatch, and a
dangling SYS-IFACE-ORDER/SYS104 registry reference from other tickets'
work) -- confirmed by running `uv run ty check` scoped to only this
ticket's two touched files, which reports "All checks passed!".

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 74 +++++++++++++++++++++++++------
 tests/test_ticket_work_and_land_finish.py | 35 +++++++++++++++
 tickets/T-1903/ticket.md                  | 18 +++++++-
 3 files changed, 112 insertions(+), 15 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 867 warning(s), 695 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
