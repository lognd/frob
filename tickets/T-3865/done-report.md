## Done report

Partial burn-down of the WAIVE004/WAIVE010 cluster T-3844 identified.

Method: WAIVE004 sites (a `frob:waive` matching 0 live findings at that
site in a full check run) were deleted outright -- a stale exemption is
dead weight that hides a real regression if the rule ever fires there
again, so it is removed, not reworded. WAIVE010 sites (a `frob:waive`
reason reading as deferred/temporary work -- "until", "pending", "for
now", "temporarily", or a WAIVE009-style promise phrase) were inspected
individually: all 7 addressable sites turned out to be permanent
exemptions whose reason text happened to use one of those words in an
unrelated (non-deferred) sense -- runtime behavior descriptions ("read
frames until a match or timeout"), enum/state names ("not PENDING"), or
provenance narration ("no pending lease remains") -- so each was
reworded to state the same permanent justification without the trigger
wording, confirmed directly against
`frob.gates._waive._reason_reads_as_deferred_work` and
`_WAIVE009_PROMISE_PHRASE_RES`. None were converted to `frob:debt`/
`until=` because none were genuinely deferred work.

Lease discipline: `frob ticket contention` plus each `.git/frob-leases/
*.json` scope glob were cross-referenced against the WAIVE004/010
finding-site file list; 17 findings across 13 files sat under another
ticket's live lease and were left untouched (see Residue below).

Scope closure: 80 of the 164 lease-free files were processed this pass
(stopped at the ~80-file/one-worktree budget the dispatch brief set).
124 lease-free WAIVE004 findings and 1 lease-free WAIVE010 finding
(src/frob/app/ticket_runner/_land_cmd.py, under another ticket's lease)
remain -- see Residue. This ticket is NOT fully drained; do not queue it
to land in its current state without either continuing the burn-down in
a follow-up pass over the residue below, or accepting a partial land and
re-opening a successor ticket for what remains (T-3844's WAIVE004/010
promotion-to-error follow-up should wait for either).

Verification per batch: `ruff check`/`ruff format --check` on the
touched files, targeted `pytest` for the touched test modules (all
green), and for the 7 WAIVE010 rewords a direct call into
`frob.gates._waive._reason_reads_as_deferred_work`/
`_WAIVE009_PROMISE_PHRASE_RES` confirming the new reason text no longer
matches. A `frob ticket land --dry-run` reached the evidence/Done-report
gate cleanly (no ruff/format/gate refusal attributable to this diff --
the one format finding it reported, tests/test_tickets_triage_dates.py,
predates this branch and is untouched by it).

Evidence note: this is a warning-severity waiver-hygiene sweep, not a
code defect a test throws/fails on, so `--check-repro` correctly reports
the bound node ids as PASSED_AT_PARENT (confirmatory-only) rather than
FAILED_AT_PARENT -- there is no pre-fix failing test to point at, only a
`frob check` finding-count delta (346 WAIVE004 lease-free findings
before this pass' scope, ~304 in-scope; 304 - 124 = 180 fixed WAIVE004,
7 - 1 = 6 fixed WAIVE010 in this pass, all lease-free). Left un-forced
(`--designate-repro-force` was available but that flag is for a
genuinely-real defect the parent-commit repro merely fails to detect --
not applicable here) -- flagging for the coordinator/reviewer rather
than overriding the gate.

Filed: T-5158 (see below) -- no OTHER out-of-scope work was discovered.

Filed: T-5158 "WAIVE004/010 residue after T-3865: 131 findings (124
lease-free in 84 files, 17 leased)" (kind=bug) -- carries the exact
lease-free file list (residue_free.txt) and the leased-site notes in its
body for a follow-up pass to continue the burn-down from.

### Changed
```
 .claude/hooks/diagnosis-nudge.py                  |    1 -
 .claude/hooks/frob-directive-guard.py             |    7 -
 scripts/artifact_smoke.py                         |   32 -
 scripts/branch_stranded_work_analysis.py          |   22 -
 scripts/check_summary.py                          |    2 -
 scripts/measure_evidence_reach.py                 |   16 -
 scripts/verify_release_ci_status.py               |    4 -
 scripts/wait_for_land_slot.py                     |    8 -
 src/frob/_cli_parsers/_core.py                    |   41 -
 src/frob/_cli_parsers/_design.py                  |    4 -
 src/frob/_cli_parsers/_explore.py                 |    8 -
 src/frob/_cli_parsers/_quality.py                 |    4 -
 src/frob/_cli_parsers/_reporting.py               |   36 -
 src/frob/app/_check_chunking_baseline.py          |    9 -
 src/frob/app/_daemon_proxy.py                     |    5 -
 src/frob/app/_json_guard.py                       |   14 -
 src/frob/app/agent_runner.py                      |    3 -
 src/frob/app/pyfmt_runner.py                      |    8 -
 src/frob/app/telemetry/_state.py                  |    7 -
 src/frob/app/ticket_runner/_rapid_sweep.py        |   20 -
 src/frob/app/ticket_runner/_verify.py             |    8 -
 src/frob/arch/_abstraction.py                     |    4 -
 src/frob/check/_python.py                         |    6 -
 src/frob/cycle/graph.py                           |    1 -
 src/frob/deploy/_conform.py                       |    7 -
 src/frob/doctor.py                                |   12 -
 src/frob/dup/_pipeline/_probe.py                  |    1 -
 src/frob/dup/_pipeline/_smt.py                    |    1 -
 src/frob/findings.py                              |   12 -
 src/frob/gates/_coverage_sites.py                 |    4 +-
 src/frob/gates/_dead_symbols.py                   |    4 -
 src/frob/gates/_debt_deprecated.py                |    1 -
 src/frob/gates/_doclink_docanchor.py              |    9 -
 src/frob/gates/_docstatus.py                      |    4 -
 src/frob/gates/_fix_engine_sync.py                |    6 -
 src/frob/gates/_fix_engine_text.py                |    8 -
 src/frob/gates/_fix_engine_tier_b.py              |    4 -
 src/frob/gates/_fmt_directives.py                 |    3 -
 src/frob/gates/_land_parity.py                    |    4 -
 src/frob/gates/_pii_structural/_keywords.py       |    3 -
 src/frob/gates/_pkg_resources.py                  |    5 -
 src/frob/gates/_refs.py                           |    7 -
 src/frob/gates/_rule_id_scan.py                   |    2 -
 src/frob/gates/_waive.py                          |    3 +-
 src/frob/gates/_wire.py                           |   17 -
 src/frob/graph/dsl.py                             |   25 -
 src/frob/graph/lock.py                            |    9 -
 src/frob/lang/__init__.py                         |    8 -
 src/frob/mutate/__init__.py                       |    6 -
 src/frob/outline/__init__.py                      |    2 -
 src/frob/process/parsers/ruff.py                  |    6 -
 src/frob/process/parsers/valgrind.py              |    9 -
 src/frob/serve/_events.py                         |    3 +-
 src/frob/strata/_claims.py                        |    4 -
 src/frob/strata/_facts.py                         |    2 -
 src/frob/strata/_host_isolation_shared.py         |    3 -
 src/frob/strata/_mode_conformance.py              |    2 -
 src/frob/tickets/_done_report.py                  |   10 -
 src/frob/tickets/_land_git_ops.py                 |    7 -
 tests/conftest.py                                 |   19 -
 tests/gates/test_scan_timeout_enforcement.py      |   32 -
 tests/test_app_daemon_proxy.py                    |    4 -
 tests/test_ci_workflow_job_summary.py             |    8 -
 tests/test_lang.py                                |    5 +-
 tests/test_ticket_leases.py                       |    4 -
 tests/test_tickets_gate_claim_evidence.py         |    2 +-
 tests/test_worktree_guard.py                      |    4 -
 tests/test_worktree_pythonpath.py                 |   10 -
 tests/unit/gates/test_pkg_resources.py            |   11 -
 tests/unit/rapid_sweep_suite/test_sweep_run.py    |    8 -
 tests/unit/rapid_sweep_suite/test_window.py       |   15 -
 tests/unit/test_close_promote_drafts.py           |    5 +-
 tests/unit/test_conftest_suite_result_status.py   |   32 -
 tests/unit/test_daemon_proxy_error_paths_t1457.py |   12 -
 tests/unit/test_dotnet_runner.py                  |   12 -
 tests/unit/test_dup_legacy_cpp.py                 |    6 -
 tests/unit/test_lifecycle_work_base.py            |   17 -
 tests/unit/test_pyfmt_runner.py                   |    9 -
 tests/unit/test_verify_language_buckets.py        |   24 -
 tickets/T-3865/done-report.md                     |  152 +++
 tickets/T-3865/ticket.md                          | 1047 ++++++++++++++++++++-
 tickets/T-5158/ticket.md                          |  155 +++
 82 files changed, 1366 insertions(+), 710 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive010Violations::test_plain_permanent_reason_does_not_warn` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription::test_relative_markdown_image_in_declared_readme_fires_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim` (pytest node id, verified passing when recorded)
