## Done report

T-2576 was redesigned by the coordinator: the original bulk backfill
(milestone: 1.0.0 into all 89 open ticket files, tickets/T-*/ticket.md in
scope) is removed -- it required a write lease on every ticket file
simultaneously and blocked M4/T-1614. Implemented the read-time-default
redesign instead: [tickets].default_milestone in frob.toml, consulted by
effective_milestone (frob.tickets._doable, M3's own function -- single
home, declared/inherited walk reused verbatim) as the TERMINAL fallback,
returning a new three-way MilestoneSource enum (DECLARED/INHERITED/
DEFAULTED) so a defaulted value never renders indistinguishable from a
real one. MILE003 (frob.gates._milestone) fires on any OPEN ticket whose
effective milestone cannot be resolved -- no declared/inherited value and
no configured default -- registered in _KNOWN_GATE_RULES so
frob:waive MILE003 binds.

11 pytest node ids bound as evidence (tests/test_gates_milestone.py, new
file). Positive controls in both directions per the ticket's own body:
declared keeps its value even with a different default configured;
inherited stays INHERITED unchanged from M3; no declared/inherited value
falls back to the configured default and renders DEFAULTED; with no
default_milestone configured, MILE003 still fires.

Filed T-2613 for a pre-existing DOCENUM001 drift on
docs/modules/gates.md (already red on main before this ticket touched
anything -- CYCLE001/TICK012 were already missing from the enumerated
member list) which MILE003's own registration adds to, but
docs/modules/gates.md is under T-2377's live lease so this ticket could
not sync the doc anchor itself.

### Changed
```
 tickets/T-2576/ticket.md           | 74 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2613/ticket.md | 28 +++++++++++++++
 2 files changed, 102 insertions(+)
```

### Evidence
- `tests/test_gates_milestone.py::TestMile003::test_fires_on_open_ticket_with_no_resolvable_milestone` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile003::test_silent_once_stamped` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile003::test_silent_on_configured_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile003::test_silent_on_inherited_value` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile003::test_terminal_ticket_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestMile003::test_no_default_configured_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestEffectiveMilestoneDefault::test_no_declared_or_inherited_falls_back_to_configured_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestEffectiveMilestoneDefault::test_declared_value_is_not_overridden_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestEffectiveMilestoneDefault::test_inherited_value_is_not_overridden_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestEffectiveMilestoneDefault::test_no_default_configured_stays_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_gates_milestone.py::TestEffectiveMilestoneDefault::test_no_root_skips_default_lookup` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2576/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2576/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2576, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
