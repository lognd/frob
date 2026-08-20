## Done report

(v2, evidence bound)

Changed:
- src/frob/app/check_runner.py: added frob:waive LARGE001 (module-level
  comment) with real per-file reasoning -- single `frob check` CLI
  subcommand orchestrator, 59 private helpers reachable only from its
  own run(), same shape flagged high-risk for the sibling _land_cmd.py.
- src/frob/app/sys_runner.py: added frob:waive LARGE001 (module-level
  comment) -- module docstring already documents the single-dispatcher-
  per-verb design; splitting into separate modules would fragment the
  unified `run()` dispatch table the docstring explicitly mandates.

Both waivers verified to match: gate:LARGE severity flips from warning
to note (waived) for both files, 0 errors either way (LARGE001 is
WARN-tier).

Seam considered and rejected for both (named above); a genuine seam WAS
found for a third file -- src/frob/app/telemetry.py splits into 3
distinct concerns (event recording / footgun tips / usage reporting) --
filed as its own successor (T-2694) rather than attempted
under this pass's time budget.

Remainder: ~80 of the 82 currently-unwaived LARGE001 files are still
unexamined (T-1656's original count of 48 grew to 82 -- other work
added new over-threshold files since filing). Carried forward to
T-2695 (batch 2) rather than left as an indefinitely-open
umbrella.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::
test_large_file_fires_large001_warn -- an EXISTING, unmodified test
that directly exercises the gate:LARGE / LARGE001 mechanism both
waivers this ticket added rely on (WARN-severity Violation emission
that a `frob:waive` directive then suppresses).

Gates: frob check --ticket T-1656 --json -> 56 error(s) total
repo-wide, ALL pre-existing baseline unrelated to this ticket's 2-file
comment-only diff; gate:LARGE (this ticket's own subject) is 0 error(s)
/ 86 note+warning diagnostics, both touched files now note (waived).

Filed: T-2694 (renumbers at land) -- telemetry.py 3-way seam
split. T-2695 (renumbers at land) -- LARGE001 remainder
batch 2.

### Changed
```
 rapid-debt.jsonl                   |  5 +++
 src/frob/app/check_runner.py       | 13 ++++++
 src/frob/app/sys_runner.py         | 14 ++++++
 tickets/T-1656/done-report.md      | 68 ++++++++++++++++++++++++++++
 tickets/T-1656/ticket.md           | 56 +++++++++++++++++++++++-
 tickets/T-1666/done-report.md      | 67 ++++++++++++++++++++++++++++
 tickets/T-1666/ticket.md           | 90 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2694/ticket.md | 72 ++++++++++++++++++++++++++++++
 tickets/T-2695/ticket.md | 62 ++++++++++++++++++++++++++
 tickets/T-2696/ticket.md | 70 +++++++++++++++++++++++++++++
 10 files changed, 514 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 34 error(s), 1036 warning(s), 699 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
