## Done report

Changed:
- src/frob/app/ticket_runner/_close_cmd.py::_promote_pending_drafts_after_close (T-2738's added function) -- split under ARCH103 into three smaller bodies: _pending_draft_ids_after_close (queue read + filter), _promote_one_pending_draft (per-draft promote + log), _report_stranded_drafts_and_exit (failure report + exit). Behavior unchanged; each new helper is private (underscore-prefixed).
- src/frob/tickets/_land.py::_check_already_landed's frob:tests directives -- corrected two frob:tests directives that pointed at TestAlreadyLandedOnMain.test_stale_rapid_debt_dirt_does_not_block_already_landed_detection / test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt (which don't exist there); the tests actually live under TestAlreadyLandedStaleRapidDebtDirt, added alongside T-2737 in the same land as T-2738. No code change, directive-only fix.

Evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts (3 tests) -- pass unchanged
- tests/unit/test_land_already_landed.py (18 tests total, including TestAlreadyLandedStaleRapidDebtDirt's 2) -- pass unchanged

Measurement (positive controls, both directions, per ticket instructions):
- `frob check --json --no-cache --ticket T-2749` (gates only, --skip-tests/ruff/ty/cycle/dup/bind/exports for speed): before fix, ARCH103 error at _close_cmd.py:1338 and DRIFT002 x2 errors at _land.py:4482-4483 both reproduced. After fix: 0 errors on either file for ARCH103/DRIFT002.
- Planted a genuine ARCH103 violation (I/O + string-format + 3 decision points) elsewhere in _close_cmd.py: still fired as ERROR, then removed (via Edit, not git checkout, after the T-1b checkout-file trap ate the real fix once and had to be reapplied).
- Planted a genuine DRIFT002 violation (bogus frob:tests directive naming a nonexistent test method) on _check_already_landed: still fired as ERROR, then removed.
- Both findings' rules are unweakened -- the fix narrows nothing about ARCH103/DRIFT002's detection, only the two flagged sites.

Filed: none (both were pre-diagnosed, correctly attributed regressions from T-2738; no out-of-scope discovery required a new ticket)

Gates: `frob check --ticket T-2749` (repo-wide, unscoped per playbook sec 6c) still shows pre-existing failures (COV, DOC, PII, SEC, TEST, TICK, CLAUDE001) unrelated to and untouched by this diff -- confirmed via `--no-cache` scan of only the two changed files: zero errors of any rule remain in src/frob/app/ticket_runner/_close_cmd.py or src/frob/tickets/_land.py after the fix. `frob check --land-parity` shows COV002 on _close_cmd.py (ambiguous multi-ticket scope coverage, a fleet-scope-state finding, not a code defect -- does not appear under --ticket T-2749 scoping) alongside other pre-existing unscoped debt (CLAUDE001, COV001/003, CYCLE001, DOC006/011, DRIFT001/002 elsewhere, PII012, SEC110, TEST001, TICK003/004), none of which are in this ticket's scope or attributable to this diff. E501 introduced by my own line-length was caught and fixed before this report.

### Changed
```
 tickets/T-2749/done-report.md | 33 +++++++++++++++++++++++++++++++++
 tickets/T-2749/ticket.md      | 11 ++++++++++-
 2 files changed, 43 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_stale_rapid_debt_dirt_does_not_block_already_landed_detection` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 19 error(s), 1069 warning(s), 705 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2742/ticket.md, DOC011@docs/modules/tickets-verify-sweep.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
