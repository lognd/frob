## Done report

T-1618's `_check_already_landed` inferred "already landed on main" purely
from an empty scope-diff on the landing branch. That signal could not
distinguish "the work is already on main" from "this ticket legitimately
touched only docs/the ledger" or "its scope globs never matched anything
it touched" -- all three produce the identical empty-diff shape. Wiring
it in unconditionally regressed 20 tests in tests/test_ticket_land.py, so
it shipped behind an opt-in flag (`--check-already-landed`) that, being
opt-in, never ran for a real land -- the defect class it targets still
reached main.

Fix: `_check_already_landed` now requires a SECOND, positive signal
alongside the empty scope-diff -- the ticket's own ledger record, read
directly off `base_ref` via a new `_ledger_ticket_at_ref` helper (factored
out of the existing `_ledger_ticket_at_merge_base`), must already show
`state: done` there. A ticket that has not yet landed cannot already be
`done` on `base_ref` (only `frob ticket close`/`land`'s own squash-apply
ever write that state), so this is genuine positive evidence the content
made it to main, not an inference from silence. The false-positive class
that forced the original opt-in (docs-only/ledger-only/scope-mismatched
tickets landing for the first time) cannot also have `state: done` on
main yet, so it no longer trips the refusal -- the check now runs
unconditionally, and the `--check-already-landed` CLI flag plus its
`ticket_check_already_landed` config field are removed end to end (CLI
parser, AppConfig, external-config allowlist, _land_cmd.py wiring,
_land.py's own `check_already_landed` parameter threaded through `land`/
`_land_precheck`).

Added a new regression test
(`test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed`)
that reproduces the exact false-positive class the old check would have
caught: a docs-only ticket whose declared scope has no hits on this
branch, but whose own record was NEVER written to main -- the check must
return `Ok(None)`, not refuse. Also rewrote the existing "refuses" test to
seed the new positive signal directly (transition the ticket to DONE in
the worktree, then write that same record onto main and commit it,
simulating a passenger-ticket land that already closed it there) since the
old test's scenario (a ticket that never existed on main at all) no longer
triggers a refusal under the new two-signal requirement -- which is
exactly the intended behavior change.

Full `tests/test_ticket_land.py` suite (233 tests, including the 20 that
regressed under the original always-on draft) still passes unmodified,
confirming the positive-signal requirement closes the false-positive gap
that forced the opt-in in the first place.

### Changed
```
 docs/modules/tickets.md                    |  84 ++++++------
 src/frob/_cli_parsers/_ticket/_progress.py |  16 ---
 src/frob/app/_config_external.py           |   2 -
 src/frob/app/config.py                     |  10 --
 src/frob/app/ticket_runner/_land_cmd.py    |   5 +-
 src/frob/tickets/_land.py                  | 198 +++++++++++++++++------------
 tests/unit/test_land_already_landed.py     |  85 ++++++++++---
 tickets.md                                 |  59 ++++++++-
 8 files changed, 286 insertions(+), 173 deletions(-)
```

### Evidence
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_declares_no_scope_at_all` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 571 warning(s), 715 waived
- error-findings: none (measured, zero errors)
