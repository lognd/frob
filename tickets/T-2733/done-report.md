## Done report

Changed:
.claude/hooks/root-cleanliness-detector.py::main (removed 1 frob:waive RENDER001)
.claude/hooks/frob-timeout-guard.py (removed 2 frob:waive RENDER001, in the FROB_AGENT guard and the timeout-quote guard)
.claude/hooks/root-write-guard.py::_deny (removed 1 frob:waive RENDER001)
.claude/hooks/pending-background-guard.py::main (removed 1 frob:waive RENDER001)
scripts/fleet_status.py (removed 6 frob:waive RENDER001: _print_verify_queue_line x3, WORKTREES print in _print_fleet_report, _print_scope_intersections x2)

Evidence:
Per-site measurement, not bulk: baseline frob check --json --no-cache --only render_lint
(pre-removal) showed ZERO RENDER001 findings anywhere in .claude/hooks/ or
scripts/fleet_status.py -- confirming T-2719's _EXEMPT_PREFIXES entry already
suppresses these sites structurally, independent of the per-line waivers.
Post-removal re-run of the identical command (--no-cache) still shows ZERO
RENDER001 findings in these files -- exemption alone holds the floor.
Positive control: the same before/after runs both show the 4 pre-existing
RENDER001 findings in src/frob/release/_cli.py unchanged (rule still fires on
a real violation elsewhere; removal is not indistinguishable from the rule
going silent).
Full-repo frob check --json --no-cache (unbudgeted) after removal: zero
diagnostics of any severity attributed to any of the 5 touched files.
git grep -n "frob:waive RENDER001" over .claude/hooks and scripts/fleet_status.py:
exit 1 (no matches) confirms all 11 directives are gone.

Filed: none

Gates: frob check --ticket T-2733 --no-cache shows 86 pre-existing errors,
none attributed to the touched files (baseline repo noise, unrelated to
this change -- confirmed by filtering the JSON report for hooks/fleet_status
paths, zero hits). RENDER001-scoped check clean per above.

### Changed
```
 tickets/T-2733/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 45 error(s), 1123 warning(s), 678 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2733, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
