## Done report

Batch 15 of the T-2359 ruff-format-only reformat epic. 10 files
re-measured against current main via ruff format --check (20 files
remaining before this batch, worktree merged current at pick time).
Format-only, no semantic changes.

File-selection note: fresh fleet_status.py + .git/frob-leases/*.json
pull at pick time (2 lands in flight: T-2755, T-2806; live leases
T-2369, T-2370, T-2373, T-2755, T-2807, T-1686 root-resident, T-2359
own). T-2373's lease had CHANGED SHAPE from the empty epic-rollup seen
in earlier batches to a real populated scope (it moved from I001
burn-down to REF001 per the coordinator's brief): src/frob/process/
parsers/ruff.py, tests/unit/test_parse.py, src/frob/gates/__init__.py,
_arch.py, _tickets_gate.py, _waive.py, src/frob/tickets/_setters.py,
tests/unit/test_ticket_new_priority_inherit_t1960.py,
tests/unit/test_waive_audit_runner.py,
tests/unit/verify/test_attribution_module_scope.py,
tests/unit/verify/test_backpressure.py, plus two docs -- confirmed
against its worktree's actual git status (all listed files genuinely
dirty there). Excluded the three of those (test_ticket_new_priority_
inherit_t1960.py, test_waive_audit_runner.py, verify/test_backpressure.py)
that overlap the remaining-20 pool. Per standing coordinator guidance,
ALSO kept excluding T-2373's six previously-identified historically-
claimed files (test_ticket_land.py, test_ticket_work_and_land_finish.py,
test_tickets_organization.py, test_tickets_priority.py,
unit/test_app_runners_batch6.py, unit/test_app_runners_t2395_
contention.py) even though they are no longer part of its current live
lease -- the coordinator's brief was explicit that these stay excluded
regardless of what the lease currently reads. Excluded T-2806's
tests/unit/test_check.py since T-2806 was actively landing per
fleet_status.py at pick time (in-flight land, about to merge that exact
file). T-2755's and T-2807's declared scopes had no overlap with the
remaining-20 pool.

Diff reviewed by hand across all 10 files: pure ruff-format formatting
changes, no logic changes. frob format needed zero ruff-check-fix
autofixes, only ruff-format-write, on all 10 files.

Evidence: ran all 10 touched test files together
(tests/unit/test_check_budget.py, test_ticket_close_bug002_t1438.py,
test_ticket_new_related.py, test_ticket_runner_ledger_mirror.py,
test_ticket_runner_ledger_verbs_export_t2647.py,
test_tickets_evidence_only_scope.py, test_unlanded_branch_work.py,
test_waive_audit_watermark.py, verify/test_drain.py,
verify/test_quarantine.py): 141 tests collected, 0 failed. No
pre-existing or reformat-induced failures found.

Filed: none -- no out-of-scope findings.
Gates: land-time gates run by frob ticket land; no waivers needed.

### Changed
```
 tickets/T-2815/ticket.md | 41 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 41 insertions(+)
```

### Evidence
- `tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 20 error(s), 959 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
