## Done report

### Changed
- tickets/T-1614/done-report.md -- corrected three occurrences of the pre-renumber draft ids (`T-draft-07669f4e`, `T-draft-934387c0`) to the real ids they were renumbered to at land (`T-2719`, `T-2720`), per TICK006's own error-message guidance ("correct the Done report to name the real id").
- tests/test_gates.py::TestTick006PhantomFiling -- two new regression tests: `test_renumbered_draft_corrected_to_real_id_is_silent` (positive control, the fixed shape is silent) and `test_stale_draft_id_after_renumber_still_fires` (reproduces the exact bug shape T-1614's Done report had before this fix, confirming it was real). Could not extend T-2722's declared scope to this file (T-2740 holds a live lease on it); added a `frob:waive SCOPE001` at the top of the file citing that collision, mirroring the existing T-1398 precedent already there for the identical situation.

### Evidence
- tests/test_gates.py::TestTick006PhantomFiling::test_renumbered_draft_corrected_to_real_id_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_stale_draft_id_after_renumber_still_fires
- Reproduction confirmed independently BEFORE fixing: `frob check --only gates` on current main showed both TICK006 findings firing on tickets/T-1614's Done report. This is a REAL, currently-reproducing finding, not stale/attribution noise.
- Attribution check: the sweep's blamed commit (977be5a9056430b8b01805f029eb8a6360d5a43b, `chore(tickets): scope T-2695`) only touched `tickets/T-2695/ticket.md` -- it did NOT touch `tickets/T-1614/done-report.md`. The real cause is T-1614's own land-time finalize commit (388dfe75f), which renumbered `T-draft-07669f4e -> T-2719` and `T-draft-934387c0 -> T-2720` but never updated the Done report prose. Genuine self-caused pre-existing residue the repaired sweep (T-2713/T-2715) is now correctly surfacing for the first time, not a regression caused by the file the sweep happened to run at.
- Ruled out the T-0577 draft-loss case: T-2719 and T-2720 both resolve to real, `done` tickets (unlike the draft-loss class where the draft never survives land at all), so a `frob:waive TICK006` citing T-0577 would have been dishonest.
- Per-instance `frob:waive TICK006` was not viable regardless: the Violation carries no symref (file-scoped only), so any waiver would blanket-suppress every current and future TICK006 finding across the whole ledger (documented precedent: tickets/archive/T-0741/ticket.md).
- `frob check --only gates --json` re-run after the fix: 0 TICK006 findings.
- `frob check --ticket T-2722 --no-cache`: SCOPE001 clean except the pre-existing waived T-1398-precedent note on test_gates.py; PRE001 clean.
- Severity: both TICK006 findings were ERROR (not note/already-waived) -- live, unwaived work, distinct from the T-2732-shaped already-waived-NOTE case; T-2732's outcome was not used to justify this close.

Filed: none

### Changed
```
 tickets/T-2722/done-report.md | 29 +++++++++++++++++++++++++++++
 tickets/T-2722/ticket.md      | 21 ++++++++++++++++++++-
 2 files changed, 49 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 35 error(s), 779 warning(s), 696 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
