## Done report

Implemented the smallest sound version of landing-time enforcement for the self-conformance drift class T-3283 diagnosed: frob.gates._sys.selfaudit_findings_touching(root, files) reuses sys_gate's own _selfaudit_violations evaluation and filters to findings whose message names one of files (a substring test -- Violation.file is always the design dir itself for every SELFAUDIT001 finding, never the real offending source file, which only appears in the underlying check's free-text detail). frob.tickets._land_squash._refuse_if_selfaudit_findings_in_touched_files calls it against the staged post-squash tree with worktree_changeset (the land's own diff), wired into _land_squash_apply_finish right after the existing (rapid-profile-skippable) pre-commit sweep -- this new check runs UNCONDITIONALLY, never skipped by rapid profile, since it is cheap (diff-scoped, not a full-repo scan). On a hit it unwinds via the same _verified_reset_root shape _apply_pre_commit_sweep_or_unwind already uses and returns LandError.PreLandUnscopedSweepFailed (reused rather than adding a new LandError variant, which would require scope on frob.tickets._models). Also satisfies the '(and frob check --ticket) gate' half of the ask: gate:SELFAUDIT already runs repo-wide and at ERROR severity under frob check --ticket (confirmed: it already surfaced the real T-1691 test_bisect.py SYS100 findings in this ticket's own scoped check output), so no additional wiring was needed there -- only the land-time synchronous path was missing. Documented in docs/modules/gates.md's existing Self-audit at land section, adding a correction that its own prior 'zero new land wiring needed' claim held only when post-merge re-verification actually runs (not SKIPPED-UNMEASURED under rapid profile, T-1575/T-1681). Added TestSelfauditFindingsTouching (5 tests: no-design-dir, finding-in-touched-file must-fire, finding-in-untouched-file/clean-model must-stay-quiet, plus a mock-based substring-filter proof independent of native availability) and TestSelfauditFindingsInTouchedFiles (3 tests: no-findings noop, findings-in-touched-files refuses-and-unwinds, finding-outside-touched-files is not this ticket's concern). All pass with strata_core natives now available in this worktree. No new tickets filed.

### Changed
```
 tickets/T-3324/ticket.md | 31 ++++++++++++++++++++++++++++++-
 1 file changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestSelfauditFindingsTouching::test_no_design_dir_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfauditFindingsTouching::test_finding_in_touched_file_is_returned` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfauditFindingsTouching::test_finding_in_untouched_file_is_filtered_out` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfauditFindingsTouching::test_clean_model_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfauditFindingsTouching::test_substring_filter_is_exact_regardless_of_native_availability` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_no_findings_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_findings_in_touched_files_refuses_and_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_finding_outside_touched_files_is_not_this_ticket_s_concern` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 17 error(s), 4179 warning(s), 865 waived
- error-findings: ARCH001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LANDPARITY001@src/frob/gates/_sys.py, LANDPARITY002@src/frob/tickets/_land_squash.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
