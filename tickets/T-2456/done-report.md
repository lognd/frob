## Done report

frob ticket land's post-land unscoped sweep is `--budget`-bounded
(previously 300s) and silently collapsed truncation into a bare
`_log.warning` -- the land proceeded and printed LAND-PROOF
verified=True indistinguishable from a clean sweep. Measured against
root's own steady-state check-budget-timing.json EMA: the 5 stage
groups sum to ~334.6s, already over the old 300s budget on a healthy
machine, so `static` was silently dropped from essentially every
post-land sweep as a matter of course (not just under unusual load).

Fix: (1) raised _POST_LAND_SWEEP_BUDGET_S 300->480, covering the
measured 334.6s total with ~145s headroom -- quantified latency trade:
common case grows from ~250s to ~335s (~85s more), only on the step
that was already silently under-covering. (2) added
budget_deferred= to the LAND-PROOF line (frob.app.ticket_runner._verify
._budget_deferred_groups_from_stdout, additive, parses the same stdout
_unscoped_error_findings already has in hand) via a new process-local
_LAST_BUDGET_DEFERRALS dict in _land_cmd.py, following the exact
precedent T-2091/T-2275 already established for
claims_reverify=/orphan_evidence_check= (module dict, popped once at
print time, surfacing-only -- never changes the returned verified
bool). A land whose sweep is still truncated on a genuinely
overloaded machine now names exactly which stage groups it could not
measure, on the very line a human or script already reads, instead of
presenting as indistinguishable from clean.

Verified end-to-end: cleared .frob/check-budget-state.json and ran
`frob check --budget 480 --json` fresh against root -- all 5 stage
groups (gates-fast/gates-native/gates-security/lint/static) now
executed, none skipped (was 3-of-5 at budget 300 on the same tree).
`lint` carries ruff/ty, so this is the direct fix for the ticket's
E501 fixture: the stage group that catches a trivial line-too-long
violation no longer silently drops out of the post-land sweep on a
normal, non-degraded machine.

Did not choose the other two options the ticket weighed: an
async-post-land-revert-obligation restructuring was a much larger,
riskier change to the land control flow for the same repo this
session already found under lease contention from a concurrent
ticket; a bare budget-only raise (no surfacing) would not meet the
"must not present as clean" bar for the residual truncation case
(genuinely overloaded machine) that 480s cannot categorically rule
out. The chosen fix is the smallest change that satisfies all three
acceptance criteria: still-lands-clean-with-no-friction (surfacing is
non-gating), the E501 fixture (budget raise), and never-presents-as-
clean-when-incomplete (budget_deferred= is unconditionally printed,
"none" on a clean run).

### Changed
```
 tickets/T-2456/ticket.md | 95 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 91 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetDeferredGroupsFromStdout::test_extracts_deferred_groups_from_json_stdout` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetDeferredGroupsFromStdout::test_empty_for_non_json_stdout` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetDeferredGroupsFromStdout::test_empty_when_no_deferral_present` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsRecordsBudgetDeferral::test_budget_truncated_run_records_deferred_groups` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsRecordsBudgetDeferral::test_clean_run_records_no_deferral` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPrintLandProofSurfacesBudgetDeferred::test_deferred_groups_named_on_the_land_proof_line` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPrintLandProofSurfacesBudgetDeferred::test_no_deferral_reports_none_not_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2456/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2456/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2456/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2456/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2456/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2456, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
