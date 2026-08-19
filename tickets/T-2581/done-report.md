## Done report

Changed:
src/frob/gates/_debt_deprecated.py::_release_open_milestone_violations
src/frob/gates/__init__.py::release_gate (wired in the new check)

Evidence:
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_cut_milestone_refuses
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_other_milestone_does_not_refuse
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_terminal_ticket_in_cut_milestone_does_not_refuse
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_no_open_tickets_in_milestone_succeeds
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_names_every_blocking_ticket
tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_queue_unavailable_does_not_crash

Positive control: an open ticket declaring the exact milestone being cut
fires REL001, naming the ticket id. Negative controls: a different
milestone, a terminal (DONE) ticket in the cut milestone, and the
explicit "no open tickets in that milestone" acceptance case all succeed
with zero violations. Two simultaneous blockers are both named in one
message, never collapsed to a count. A malformed ledger degrades to
"skip this check" rather than crashing the whole release gate.

Uses the EFFECTIVE milestone (frob.tickets._doable.effective_milestone --
declared/inherited/defaulted) throughout, matching MILE001-004 and
doable's own display, per the ticket's explicit requirement.

Filed: none.

Gates: uv run frob check --ticket T-2581 -- gate:SCOPE 0 errors, gate:AFFECT
0 errors, gate:REL 0 errors/1 warning, gate:COV 15 errors (same baseline
count as T-2580's post-merge measurement, i.e. no new COV002 finding from
this diff -- the new test class carries its own frob:ticket T-2581
directive). Remaining gate-summary FAILs (ruff-format repo-wide baseline,
gate:PERF/PII/SEC/SELFAUDIT/TICK/WIRE/DOC/DOCENUM/DRIFT/RENDER/PRE/
frob-cycle) are pre-existing repo-wide baseline failures unrelated to this
diff.
uv run pytest tests/test_gates.py -k "TestReleaseOpenMilestoneViolations or
release_gate or Debt or Deprecated": SUITE-RESULT exitstatus=0, 29 passed
(6 new + 23 pre-existing REL001/debt/deprecated tests untouched by this
change). tests/test_release.py: SUITE-RESULT exitstatus=0, 57 passed.

### Changed
```
 src/frob/gates/__init__.py         |  10 ++-
 src/frob/gates/_debt_deprecated.py |  77 ++++++++++++++++++++++
 tests/test_gates.py                | 127 +++++++++++++++++++++++++++++++++----
 tickets/T-2581/ticket.md           |  30 ++++++++-
 4 files changed, 227 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_cut_milestone_refuses` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_open_ticket_in_other_milestone_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_terminal_ticket_in_cut_milestone_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_no_open_tickets_in_milestone_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_names_every_blocking_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestReleaseOpenMilestoneViolations::test_queue_unavailable_does_not_crash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/m5-m6-series/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2581, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
