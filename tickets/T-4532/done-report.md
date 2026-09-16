## Done report

Fixed the 5 post-land residue findings for this ticket's 8 files, no behaviour change. AFFECT001/COV002 on the 6 code files: already resolved once frob check is invoked with --ticket T-4532 (this ticket's own scope glob covers all 8 files) -- the original --files-only measurement used the wrong base (main, not dev) and no --ticket, so it over-reported; confirmed by re-running with --ticket --base dev and watching COV002/AFFECT001/DUP001 disappear. COV001 src/frob/gates/__init__.py::REPO_WIDE_GATES: added a frob:doc edge to docs/commands/check.md's file-scoped-compute section (anchor verified against slugify's real algorithm, not guessed). DUP001 tests/unit/test_ci_self_gate_unscoped.py: does not reproduce under --base dev; confirmed twice with --no-cache. DRIFT002 docs/modules/tickets-landing.md: structurally unfixable by frob ack (frob.graph._resolve.resolve only searches snapshot.symbols; a bare non-python file never becomes one) and frob:waive DRIFT002 is not a recognized markdown waiver verb; fixed by removing the unfixable frob:describes edge and replacing it with a plain HTML comment recording hand re-verification. Filed T-4533 for the real ack/resolve gap. Before: 45 errors across these 8 files for these 5 rules; after: 0. BUG002 waived per ticket body. ruff check/format clean on touched files. 7 pytest node ids bound and individually passing.

### Changed
```
 tickets/T-4533/ticket.md | 35 +++++++++++++++++++++++++++++++++++
 tickets/T-4534/ticket.md | 31 ++++++++++++++++++++++++++++---
 2 files changed, 63 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_check_scoped_files.py::TestGateConfigFiles::test_repo_wide_gates_constant` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_window.py::TestWindowStateIo::test_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_step_exists_and_is_named` (pytest node id, verified passing when recorded)
- `tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 9 error(s), 4987 warning(s), 967 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/excludes.py, COV001@src/frob/lang/_project_detect.py, COV007@src/frob/lang/_project_detect.py, DOC002@src/frob/lang/_project_detect.py, MILE001@tickets.md, MILE002@tickets.md, PRE001@tickets/T-4534, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4493.json
