## Done report

Confirmed the ticket's own finding: `_run_cycle` (`src/frob/check/_python.
py`) built its `Diagnostic` list and returned it straight into its
`ToolResult` with zero calls into `frob.gates._waive` anywhere in this
module or `frob.check.__init__` -- a `# frob:waive CYCLE001 reason="..."`
comment did not change the diagnostic text at all, byte-for-byte, before
or after (reproduced by hand first, then in `tests/unit/test_cycle_waiver.
py::TestCycleWaiverPipeline::test_matching_waiver_suppresses_the_cycle`,
which genuinely fails at the pre-fix parent commit).

Fix, following the T-0375 ARCH001 precedent exactly (`_arch001_
violations`/`_arch_long_function_waived_symrefs`, same file): added
`_cycle001_violations` (maps each CYCLE001 `Diagnostic` to a `frob.gates.
Violation` twin, `symref=None` since a cycle's `file` is a deterministic
REPRESENTATIVE node, not a specific symbol) and `_cycle_apply_waivers`
(runs those `Violation`s through the real `_apply_waivers`/`_match_waiver`
spine via the already-cached `_cached_snapshot`, then drops any diagnostic
whose file matched a waived violation). `_run_cycle` now calls `_cycle_
apply_waivers` before building its `ToolResult`. No changes were needed
to `frob.gates.__init__` or `frob.gates._waive` themselves -- both are
consumed via their existing public re-exports, exactly the same surface
`_arch_long_function_waived_symrefs` already uses, so this stays entirely
inside `frob.check`.

Note on scope: the ticket's own declared scope named `src/frob/gates/
__init__.py`, but a live in-progress lease (T-2575) on that file made it
uneditable; confirmed no edit to it was actually needed (the fix only
imports its existing public names) and narrowed T-2584's own scope to
drop that file via `frob ticket scope --remove` before starting.

Positive/negative controls (ticket's own acceptance criteria), all in
`tests/unit/test_cycle_waiver.py`:

- `test_unwaived_cycle_reports` -- a planted 2-file cycle with no waiver
  reports CYCLE001 unwaived.
- `test_matching_waiver_suppresses_the_cycle` -- a `frob:waive CYCLE001
  reason="..."` in the cycle's representative file suppresses it
  entirely. This is the ticket's own repro and its designated evidence.
- `test_unrelated_files_waiver_does_not_suppress` -- negative control: a
  waiver in a THIRD file not part of the cycle does not suppress it.
- `test_missing_reason_is_not_silently_honored` -- a waiver with no
  `reason=` does not suppress anything either (WAIVE001 inherited from
  the real pipeline, not bypassed by a hand-rolled shortcut).

Also verified by hand against a real fixture tree, across separate CLI-
equivalent process invocations (not the in-process `_snapshot_cache`,
which memoizes per scan root within one process and would otherwise mask
a real repro): unwaived reports 1 finding; matching-file waiver drops it
to 0; unrelated-file waiver leaves it at 1.

`frob check --only suppress --ticket T-2584` (WAIVE001/002/004) is clean
-- the waiver still carries every existing guard (missing reason=,
never-matches, unused), nothing was weakened to make this land, matching
this repo's standing "rule-level liveness escapes are unsound" doctrine.

Filed: none new.

Gates: `frob check --only docanchor --only drift --only render_lint
--only prework --only scope --only tickets --only affect_drift --only
suppress --ticket T-2584` -- 0 SCOPE/AFFECT/suppress errors; the 12
remaining errors (refs_schema draft-ref, DRIFT001 on ticket_runner/
_verify.py, RENDER001 on release/_cli.py, TICK003/004 archive-threshold
debt) are pre-existing repo-wide debt with zero mentions of cycle/check
files in the findings text. `frob check --only test --ticket T-2584`:
the one TEST001 error is `strata/_multifile.py::SealedGrantSet.from_root_
node`, unrelated to this ticket's files.

### Changed
```
 src/frob/check/_python.py       |  71 +++++++++++++++++++++++-
 tests/unit/test_cycle_waiver.py | 118 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2584/ticket.md        |  16 +++++-
 3 files changed, 202 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unwaived_cycle_reports` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_matching_waiver_suppresses_the_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unrelated_files_waiver_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_missing_reason_is_not_silently_honored` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2584/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2584/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
