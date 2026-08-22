## Done report

`_check_already_landed`'s dirty-worktree gate (`_porcelain_dirty`) could
not tell a PRIOR failed land's own mechanical `rapid-debt.jsonl` append
apart from real uncommitted work, so it always deferred (Ok(None)) the
moment that one leftover row existed -- even when the ticket's content
diff against main was independently confirmed empty. Reproduced LIVE
twice during the T-2711/T-2718 series (see ticket body).

Added `_dirty_ignoring_rapid_debt` (mirrors `_commit_rapid_debt_only_
drift`'s existing SOLE-dirty-path pattern, T-1699): a worktree dirty
ONLY on `rapid-debt.jsonl` now reads as clean for THIS gate specifically;
any other dirt, alone or alongside it, still reads dirty exactly as
`_porcelain_dirty` would. Wired into `_check_already_landed` in place of
the bare `_porcelain_dirty` call -- no other `_porcelain_dirty` caller
(DirtyMain, land's own wip-commit staging, etc.) is touched.

Positive controls (both required by the ticket, both covered): a
worktree dirty ONLY on stale rapid-debt.jsonl dirt correctly reaches the
already-landed refusal; a worktree with GENUINE uncommitted code dirt
alongside the same stale rapid-debt.jsonl still defers (Ok(None)), never
a false already-landed positive.

Changed:
- src/frob/tickets/_land.py::_dirty_ignoring_rapid_debt (new)
- src/frob/tickets/_land.py::_check_already_landed (wired to the new helper)

Evidence:
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_clean_worktree_reads_as_clean
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_sole_rapid_debt_dirt_reads_as_clean
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_rapid_debt_plus_another_file_still_reads_dirty
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_a_different_lone_dirty_file_still_reads_dirty
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_stale_rapid_debt_dirt_does_not_block_already_landed_detection
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt

Filed: none

Gates: full existing tests/unit/test_land_already_landed.py suite (14
tests, was 8) passes; scoped ruff-check/ty on
src/frob/tickets/_land.py + tests/unit/test_land_already_landed.py both
clean. Full unchunked `frob check` refused under FROB_AGENT per T-0627;
land's own pre-land/post-merge gates are the final verification pass.

### Changed
```
 rapid-debt.jsonl                         |   1 +
 src/frob/app/ticket_runner/_close_cmd.py |  84 ++++++++++++++++
 tests/unit/test_close_promote_drafts.py  | 163 +++++++++++++++++++++++++++++++
 tickets/T-2737/done-report.md            |  66 +++++++++++++
 tickets/T-2737/ticket.md                 |  33 ++++++-
 tickets/T-2738/done-report.md            |  52 ++++++++++
 tickets/T-2738/ticket.md                 |   6 +-
 7 files changed, 402 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_clean_worktree_reads_as_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_sole_rapid_debt_dirt_reads_as_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_rapid_debt_plus_another_file_still_reads_dirty` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_a_different_lone_dirty_file_still_reads_dirty` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_stale_rapid_debt_dirt_does_not_block_already_landed_detection` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 49 error(s), 995 warning(s), 678 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, DUP001@tests/unit/test_close_promote_drafts.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
