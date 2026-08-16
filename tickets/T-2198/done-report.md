## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_land_plan_tick_findings (new)
- src/frob/app/ticket_runner/_land_cmd.py::_land_plan_pre_merge_tick_baseline (new)
- src/frob/app/ticket_runner/_land_cmd.py::_land_plan_check_ticks_fn (rewritten: attribution diff, not global count)
- src/frob/app/ticket_runner/_land_cmd.py::_land_plan_cmd (wired to capture pre-merge baseline)

Fix: `frob ticket land --plan`'s TICK-gate re-check now compares a
pre-merge baseline (`_land_plan_pre_merge_tick_baseline`, scanned via a
detached T-1463 snapshot worktree so the scan's own scratch-artifact side
effects cannot dirty root before land_plan's own dirty check) against the
post-merge scan `land_plan` already ran, and refuses only on NEW
(rule_id, file) TICK findings the landing diff itself introduced. A
pre-existing rotting-epic TICK004 finding (unrelated to the landing
worktree) survives the diff unchanged and no longer blocks the land.
Also reads structured `frob check --json` output
(`_parse_error_findings_from_stdout`) instead of regexing rendered CLI
text -- the second measured defect (a wording/column change used to
silently flip the result to None/skip).

Evidence:
- tests/test_ticket_land.py::TestLandPlan::test_pre_existing_tick004_does_not_block_ledger_only_plan_land
  (--accepts 0, 1, 2 -- all three acceptance criteria)
  --check-repro: FAILED_AT_PARENT at 45b35c165 (repro-only commit) --
  confirmed real repro, not confirmatory-only.
- tests/test_ticket_land.py -k TestLandPlan: 11 passed (was 10 pre-fix +
  this new repro), 0 failed.
- tests/test_ticket_land.py full file: 273 passed, 4 failed -- all 4
  failures pre-existing/unrelated to this change (TestLand.
  test_refuses_on_dirty_main, TestLedgerV2LandMergeStory.
  test_same_ticket_conflict_surfaces_loudly_no_splice, TestUvLockSync.
  test_dirty_lock_with_other_change_still_refuses, TestUvLockSync.
  test_dirty_lock_version_plus_other_line_still_refuses -- matches the
  playbook's documented "4 known pre-existing failures" count exactly;
  none touch land --plan/TICK-gate code).
- `uv run frob check --only lint --ticket T-2198 --json`: 1 pre-existing
  ruff-check E501 at _land_cmd.py:3463 (unrelated function, not touched
  by this ticket), 118 ruff-format reformats repo-wide (pre-existing,
  absorbed automatically by `frob ticket land`'s fmt step per playbook
  section 0.5) -- zero findings on the lines this ticket touched.

Filed: none (no out-of-scope discoveries this ticket).

Gates: `frob check --only lint --ticket T-2198` clean on touched lines
(pre-existing repo-wide findings noted above, none in scope/touched by
this ticket, none waived).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 179 ++++++++++++++++++++++++++------
 tests/test_ticket_land.py               |  88 ++++++++++++++++
 tickets/T-2198/ticket.md                |  17 ++-
 3 files changed, 247 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandPlan::test_pre_existing_tick004_does_not_block_ledger_only_plan_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2198/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2198, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
