## Done report

Batch 14 of the T-2359 ruff-format-only reformat epic. 13 files
re-measured against current main via ruff format --check (32 files
remaining before this batch, worktree merged current at pick time).
Format-only, no semantic changes.

File-selection note: fresh fleet_status.py + .git/frob-leases/*.json
pull at pick time. Live leases: T-2369, T-2370, T-2373, T-2755, T-2809
(plus T-1686 root-resident, T-2359 own). T-2369/T-2370/T-2373 all read
lease scope: [] (epic-rollup shape, known under-report). Checked each
live worktree's actual git status: T-2369/T-2370/T-2755/T-2809 all clean
(no genuine uncommitted edits); T-2373 alone had real dirty files
(src/frob/gates/__init__.py, _arch.py, _tickets_gate.py,
tickets/_setters.py, tests/unit/test_ticket_new_priority_inherit_t1960.py,
tests/unit/test_waive_audit_runner.py,
tests/unit/verify/test_attribution_module_scope.py,
tests/unit/verify/test_backpressure.py). Excluded the three of those
that overlap the remaining-32 pool. Also kept excluding T-2373's
previously-identified historically-claimed files per standing guidance
(test_ticket_land.py, test_ticket_work_and_land_finish.py,
test_tickets_organization.py, test_tickets_priority.py,
unit/test_app_runners_batch6.py, unit/test_app_runners_t2395_contention.py)
even though its lease reads empty, since that shape under-reports.
Excluded T-2806's declared tests/unit/test_check.py. T-2755's and
T-2809's declared scopes (fleet_status.py/coordinator note) had no
overlap with the remaining-32 pool.

Diff reviewed by hand across all 13 files: pure ruff-format
whitespace/line-wrap changes (43 insertions, 39 deletions total across
the batch), no logic changes. frob format needed zero ruff-check-fix
autofixes, only ruff-format-write, on all 13 files.

Test results: 11 of 13 touched test files pass clean (179 tests, 0
failed) when run together
(test_type_name_only_regression_t1957.py, test_waive.py [strata],
test_app_sys_capacity.py, test_app_sys_threats.py, test_app_sys_trace.py,
test_lang_primitives.py, test_lang_strata.py,
test_new_ticket_scope_overlap_warning.py, test_ticket_close_bug002_t1427.py,
test_app_runners.py, test_app_runners_t0976_mutation_evidence.py).
Two failures surfaced in the remaining two files
(test_app_runners_batch7.py::TestTicketStart::test_start_refuses_over_broad_scope,
test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty)
-- both reproduced byte-for-byte on unmodified main (root checkout,
clean at main tip b63da6917, ran with -p no:xdist to rule out a crashed
xdist worker) BEFORE landing, confirming both are pre-existing failures
unrelated to this reformat, not caused by the diff.

Filed: none -- no out-of-scope findings.
Gates: land-time gates run by frob ticket land; no waivers needed.

### Changed
```
 tickets/T-2814/ticket.md | 44 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 44 insertions(+)
```

### Evidence
- `tests/unit/dup/test_type_name_only_regression_t1957.py::TestTypeNameOnlyCloneMissedByDefault::test_default_config_does_not_catch_the_function_pair` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 1048 warning(s), 713 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2814, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
