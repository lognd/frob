## Done report

M4b: MILE004 (ERROR) -- reconcile multiple `runs_last` tickets sharing
one milestone. Ambiguity between two or more runs-last tickets in the
SAME effective milestone (declared/inherited/defaulted, via
`frob.tickets._doable.effective_milestone`) is now a build failure
unless resolved by a real `blocked_by` edge (either direction) or an
explicit, TWO-SIDED `runs_last_parallel_safe=True` declaration.

Model (src/frob/tickets/_models.py): `runs_last_parallel_safe: bool =
False` + `runs_last_parallel_safe_reason: str | None = None` added to
both `Ticket` and `TicketSpec`, same bool+reason declaration shape
`scope_breadth_ack`/`scope_breadth_ack_reason` already established for
TICK009 -- per the ticket's own instruction, not a new invented shape,
and specifically NOT `frob:waive MILE004` (that would suppress the
finding without recording a structured, queryable WHY). Added
`TicketError.RunsLastParallelSafeReasonMissing` for a future setter's
validation (setter/CLI wiring itself is out of this ticket's declared
scope -- see the filed follow-up below).

Gate (src/frob/gates/_milestone.py): `_mile004_unordered_runs_last`
groups OPEN `runs_last` tickets by effective milestone, then for every
pair within a group flags it UNLESS `_ordered` (a `blocked_by` edge
either direction) or both sides declare `runs_last_parallel_safe=True`.
The pre-existing T-1613 sibling carve-out in `_other_open_tickets`
(frob.tickets._doable) is untouched -- MILE004 only detects when that
carve-out's coexistence needed an explicit decision that was never made
(the T-1614 concrete instance the ticket names), it does not change
what makes two runs-last tickets dispatchable. Registered in the
existing "milestone" gate stage (no new stage) alongside MILE003.

MILE004 registered in `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py,
scope added with reason) so `frob:waive MILE004` binds. docs/modules/
gates.md's frob:enumerates member list needs the same sync but is under
T-2377's live lease -- T-2613 already tracks this exact DOCENUM001 gap
(confirmed pre-existing on main, referenced rather than re-filed or
force-edited).

Evidence (7 tests added to the pre-existing tests/test_gates_milestone.py,
covering all four of the ticket's named positive controls plus three
more: two unordered fires; a blocked_by edge resolves it; a two-sided
parallel-safe declaration resolves it; a ONE-sided declaration still
fires (not one of the four named controls, the natural must-fail
complement); a single runs-last ticket never fires; two runs-last
tickets in DIFFERENT milestones never pair; a terminal sibling is
excluded from pairing.

Filed T-2624 (renumbers at land): CLI wiring
(`frob ticket new --runs-last-parallel-safe --runs-last-parallel-safe-
reason`, and a retroactive `set_runs_last_parallel_safe` setter +
`frob ticket runs-last-parallel-safe <id>` verb) -- out of T-2579's
declared scope (no `_setters.py`/`_new_renumber.py`/`_mutate.py` in
scope). Until that lands, `runs_last_parallel_safe` is settable only by
direct `Ticket` construction / hand-editing the ledger, which is how
this ticket's own tests exercise MILE004 (fine for gate-logic
verification; not fine for a real operator making the declaration).

Pre-existing DRIFT001 findings on src/frob/app/ticket_runner/_verify.py
and src/frob/tickets/__init__.py (neither file touched by this ticket)
are unrelated to this change -- confirmed present before T-2579 touched
anything (same two findings observed during T-2578's own land), left
as-is, out of scope.

### Changed
```
 tickets/T-2579/ticket.md           | 25 +++++++++++++++++++
 tickets/T-2624/ticket.md | 51 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 76 insertions(+)
```

### Evidence
- `tests/test_gates_milestone.py::TestMile004::test_two_unordered_runs_last_in_one_milestone_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_blocked_by_edge_resolves_the_pair` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_declared_parallel_safe_resolves_the_pair` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_one_sided_parallel_safe_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_single_runs_last_ticket_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_different_milestones_never_pair` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile004::test_terminal_sibling_excluded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_milestone.py, ARCH001@src/frob/gates/_milestone.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2579/src/frob/gates/_milestone.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
