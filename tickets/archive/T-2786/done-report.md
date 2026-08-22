## Done report

Changed:
tests/unit/gates/test_cov007_entrypoint_exemption.py
tests/unit/gates/test_examined_sites.py
tests/unit/gates/test_lexical_selfcheck.py
tests/unit/gates/test_port_selfcheck.py
tests/unit/gates/test_refs.py
tests/unit/gates/test_sys_selfaudit.py
tests/unit/graph/test_dsl_markdown_waive.py
tests/unit/graph/test_dsl_mention_escape.py
tests/unit/strata/test_conform_eval_needle.py
tests/unit/strata/test_export.py
tests/unit/strata/test_facts.py
tests/unit/strata/test_mutation_audit.py
tests/unit/telemetry/test_rule_counts.py

Evidence: 12 pytest node ids bound (one representative test per touched
file, excluding test_conform_eval_needle.py -- see below), all pass.
Full-batch run: 131 collected, 1 pre-existing failure (not caused by
this change), 130 pass when that one is excluded.

Pre-existing failure: tests/unit/strata/test_conform_eval_needle.py::
TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
fails both in this worktree AND on unmodified main at the primary
checkout (reproduced directly against /home/logan/projects/frob at
main tip eeff120d4, same assertion shape, different violation count
due to other in-flight tickets' scope). This ticket's own diff to that
file is a single blank-line removal (ruff-format only) -- unrelated to
the failure. Not fixed here; pre-existing and out of this batch's scope.

Filed: this is child batch 5 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (two files also picked up an
import-sort / quote-style fix) + ruff-format-write per file; diff
reviewed by hand, format-only, no semantic changes.

### Changed
```
 tickets/T-2786/ticket.md | 55 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```

### Evidence
- `tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_uninstrumented_family_reports_not_examined` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_new_lexical_decider_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_import_alias_reaches_the_real_target_not_the_alias_name` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_a_genuinely_unhonored_rule_is_reported_unparsed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_masks_a_mention_span_to_same_length_dots` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export.py::TestExportK8sNetpol::test_deny_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_facts.py::TestBuildFacts::test_builds_and_indexes_a_valid_model` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero` (pytest node id, verified passing when recorded)
- `tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_counts_kept_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 19 error(s), 937 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
