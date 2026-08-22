## Done report

Changed: tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent.test_doable_sprint_filter

Cause: the fixture filed two tickets titled "in sprint" / "not in sprint",
which the T-1995 duplicate-title guard (correctly) reads as an 82% match
and refuses without --ack-related. Fixed by renaming the fixture titles to
genuinely distinct strings ("sprint alpha rollout" / "backlog cleanup
task") -- the test's actual subject (sprint-membership filtering) is
carried by ticket_sprint, not by title text, so this does not change what
is covered. Did not weaken or ack-related the guard.

Same-class sweep: ran the full tests/unit/ selection (not just the scoped
file) on unmodified main before fixing, to find the denominator. 20 tests
were red; grepped every failure's log for the guard's own signature
("closely match this title") -- it appears exactly once, in this test.
The other 19 unit-test failures on main are pre-existing and unrelated
(renumber CLI SystemExit/DID NOT RAISE behavior in
test_app_runners_batch7.py, strata self-conform/golden-export/mutation-
audit failures, exports/lang-parse-guard/mutation-sweep-queue failures).
None share the duplicate-title-guard cause. T-2602's own class count is
therefore 1 of 1 -- no siblings found, nothing else to fix under this
ticket.

Evidence: tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter
  designated via --designate-repro, verdict FAILED_AT_PARENT (confirmed
  with `frob ticket evidence T-2602 --check-repro` before designating).

Positive controls:
  - fixed test passes on the fix commit (pytest, 5/5 in the file green)
  - the T-1995 guard still refuses a genuine near-duplicate filing without
    --ack-related: tests/unit/test_ticket_new_related.py (10/10 green,
    unmodified, covers this refusal path directly)
  - the fixed test still asserts sprint filtering by parent -- unchanged
    assertions on "T-0001 <title>" present / "T-0002" absent in doable
    --sprint output

Filed: none -- the same-class sweep found no other tickets sharing the
T-1995 duplicate-title-guard failure class.

Gates: frob check --ticket T-2602 -- no findings reference this ticket's
touched file; all repo-wide gate failures shown (COV/DOC/TICK/WIRE/SEC/
etc.) are pre-existing baseline noise unrelated to this one-line fixture
rename (per the gate:scope-note, only SCOPE/PREWORK/COV002/TODO001/FMT/
AFFECT are ticket-scoped, everything else is repo-wide).

### Changed
```
 tests/unit/test_app_runners_t0715_sprint_tier.py | 14 +++++++++++---
 tickets/T-2602/ticket.md                         |  6 ++++--
 2 files changed, 15 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2602-t2603/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2602, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
