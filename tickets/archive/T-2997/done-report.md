## Done report

Changed:
src/frob/tickets/_evidence.py::record_rapid_debt
tests/unit/test_rapid_debt.py
tests/unit/test_rapid_sweep.py::_seed_repo
tests/unit/test_rapid_sweep.py::TestCommitRapidDebt
tests/unit/test_gitattributes_merge.py (TestRapidDebtUnionMerge -> TestForceOverridesUnionMerge)
tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization
.gitattributes (removed rapid-debt.jsonl merge=union / eol=lf pins)
docs/modules/tickets-merge-driver.md
docs/modules/tickets-verify-sweep.md
rapid-debt.jsonl (untracked; 3348 lines migrated to .frob/rapid-debt.jsonl on local disk, not committed)
changelog.d/T-2997.md

Evidence:
tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_lives_under_dot_frob_not_the_tracked_root
tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_creates_dot_frob_when_missing
tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_leaves_the_repo_clean
tests/unit/test_gitattributes_merge.py::TestForceOverridesUnionMerge::test_two_branches_appending_different_records_both_survive
tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_rapid_debt_no_longer_carries_an_explicit_pin

Premise: held and measured worse than filed. rapid-debt.jsonl was 3,348 lines / ~396KB at start of this ticket (vs 2,882/345KB at filing) with 47 references across src/, confirming continued unbounded growth and merge-conflict-hotspot exposure.

What changed: moved rapid-debt.jsonl's write location from the tracked repo root to gitignored `.frob/rapid-debt.jsonl`, per the owner decision already recorded on this ticket (2026-08-26). `record_rapid_debt` now creates `.frob/` if missing and writes there. Removed the now-unneeded `/rapid-debt.jsonl merge=union` and `/rapid-debt.jsonl text eol=lf` .gitattributes pins (force-overrides.jsonl, the sibling ledger, keeps both -- retargeted TestRapidDebtUnionMerge's coverage of the merge=union mechanism onto it so the mechanism itself stays tested). `_commit_rapid_debt` and the SOLE-dirty-path/DirtyMain special-casing in _land.py/_land_git_ops.py/_rapid_sweep.py were left in place uninverted -- they degrade gracefully into permanent no-ops now that the file is never tracked or dirty (verified: `git status --porcelain -- rapid-debt.jsonl` is always empty for a gitignored file), rather than being ripped out at risk in this same change. Filed as a documented follow-up below rather than silently left unexplained.

Existing 3,348 lines: migrated to `.frob/rapid-debt.jsonl` on this worktree's local disk (not committed -- `.frob/` is gitignored). Pre-move history remains reachable via `git log`/`git show` on any commit before this ticket's land; it is not carried forward as tracked content. Stated explicitly per the ticket's own acceptance bar.

Fresh-checkout dependency check (ticket's own requirement): grepped every reader/writer of `rapid-debt.jsonl` in src/ (47 references) -- the sole writer is `record_rapid_debt`, now fixed; every other reference is either the `_commit_rapid_debt`/DirtyMain machinery above (auto-degrades to a no-op, see above) or comments/docstrings, both updated. No consumer reads this file from a fresh clone or another machine; nothing depends on it surviving a clone.

Real risk found and reported, not silently patched: `frob clean --deep` (tier 3) `shutil.rmtree`s the entire `.frob/` directory (src/frob/clean/_rules.py `_TIER3_PATTERNS`), which would now also destroy `.frob/rapid-debt.jsonl`. This is a genuine tension with "do not silently discard it" -- flagging it here rather than expanding this ticket's scope into src/frob/clean/. Filed T-3220 (renumbers to a real id on land; kind=bug, scope=src/frob/clean/_rules.py,src/frob/clean/_core.py) to decide and implement a carve-out (e.g. exclude rapid-debt.jsonl from the tier-3 walk, or move the write target outside the `.frob/clean --deep` blast radius).

Filed: T-3220 (frob clean --deep wholesale-deletes .frob/, which would now also delete rapid-debt.jsonl -- needs a carve-out or the owner's explicit acceptance of that data-loss mode too)

Gates: `frob check --ticket T-2997 --only affect_drift` clean for AFFECT001 (both doc anchors updated); `frob check --ticket T-2997 --only fmt` clean. Remaining DRIFT001/WAIVE010 findings from the unscoped repo-wide portion of `frob check --ticket T-2997` are pre-existing and unrelated to this ticket's touched files (test_logging_module.py, test_reopen_ticket.py, an unrelated T-2993 waiver) -- verified by grep, none reference rapid-debt.jsonl/_evidence.py/.gitattributes/the touched test files.

Test evidence: `pytest tests/unit/test_rapid_debt.py tests/unit/test_rapid_sweep.py tests/unit/test_gitattributes_merge.py tests/unit/test_gitattributes_crlf_normalization.py` all green (177 tests). `frob test --base main` touched-set run: 1 failure, `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion` -- confirmed PRE-EXISTING by reproducing it against the unmodified `.gitattributes` (git show HEAD) with my other changes still in place: fails identically, unrelated to this ticket (autocrlf env-dependent, not rapid-debt-related). `tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_true_verdict_lands_normally` also fails on this worktree but touches none of this ticket's files (T-3135 warm-sweep-stage path assertion) -- confirmed unrelated, reproduces without any of my edits present (file never modified by this ticket).

### Changed
```
 tickets/T-2997/ticket.md           | 103 ++++++++++++++++++++++++++++++++++++-
 tickets/T-3220/ticket.md |  31 +++++++++++
 2 files changed, 133 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_lives_under_dot_frob_not_the_tracked_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_creates_dot_frob_when_missing` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_leaves_the_repo_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestForceOverridesUnionMerge::test_two_branches_appending_different_records_both_survive` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_rapid_debt_no_longer_carries_an_explicit_pin` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 98 error(s), 1138 warning(s), 882 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-1873, COV003@tickets/T-2611, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2997/src/frob/tickets/_evidence.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
