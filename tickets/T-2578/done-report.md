## Done report

M4: rescope `runs_last` from GLOBAL open-ticket scope to the ticket's own
EFFECTIVE milestone (declared/inherited/defaulted, same resolution
`doable`'s display already uses via `effective_milestone`).

`_other_open_tickets` (src/frob/tickets/_doable.py) now accepts `root` and
resolves `ticket`'s effective milestone first. When it is `None` (no
milestone anywhere in the chain, and no configured default), behavior is
byte-for-byte identical to pre-T-2578: every other non-runs-last open
ticket, repo-wide, counts. When it resolves to a real value, only OTHER
open tickets whose own effective milestone matches count -- open work in
a different milestone no longer blocks a runs-last ticket. The T-1613
sibling carve-out (fellow runs-last tickets never count against each
other) is preserved unchanged. `_doable_candidates`'s one call site now
threads `root` through.

Evidence (6 new tests in tests/test_tickets_milestone_runs_last.py,
synthetic fixtures per the ticket's corrected evidence note -- T-1614
itself has runs_last=false today and was not used):
- unmilestoned runs-last: blocked by any other open ticket (back-compat
  control), and becomes doable once that ticket is terminal.
- milestoned runs-last: blocked by another OPEN ticket in the SAME
  milestone, and becomes doable once that ticket is terminal.
- milestoned runs-last: NOT blocked by open work in a DIFFERENT
  milestone (the scoping proof).
- two runs-last siblings sharing one milestone: neither blocks the
  other (sibling carve-out preserved).

Pre-existing DRIFT001 findings on src/frob/app/ticket_runner/_verify.py
and src/frob/tickets/__init__.py (neither file touched by this ticket)
are unrelated to this change -- left as-is, out of scope.

### Changed
```
 tickets/T-2578/ticket.md | 17 ++++++++++++++++-
 1 file changed, 16 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_keeps_global_semantics` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_becomes_doable_once_all_else_terminal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_blocked_by_same_milestone_open_work` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_doable_once_same_milestone_work_terminal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_not_blocked_by_other_milestone_open_work` (pytest node id, verified passing when recorded)
- `tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_runs_last_sibling_carve_out_preserved_within_a_milestone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2578, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
