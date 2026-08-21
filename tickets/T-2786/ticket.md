---
id: T-2786
title: 'Reformat batch 5/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_cov007_entrypoint_exemption.py
- tests/unit/gates/test_examined_sites.py
- tests/unit/gates/test_lexical_selfcheck.py
- tests/unit/gates/test_port_selfcheck.py
- tests/unit/gates/test_refs.py
- tests/unit/gates/test_sys_selfaudit.py
- tests/unit/graph/test_dsl_markdown_waive.py
- tests/unit/graph/test_dsl_mention_escape.py
- tests/unit/telemetry/test_rule_counts.py
- tests/unit/strata/test_conform_eval_needle.py
- tests/unit/strata/test_export.py
- tests/unit/strata/test_facts.py
- tests/unit/strata/test_mutation_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_uninstrumented_family_reports_not_examined
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_new_lexical_decider_is_flagged
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged
- tests/unit/gates/test_refs.py::TestResolvedImportChannel::test_import_alias_reaches_the_real_target_not_the_alias_name
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_a_genuinely_unhonored_rule_is_reported_unparsed
- tests/unit/graph/test_dsl_mention_escape.py::TestMaskFrobMentions::test_masks_a_mention_span_to_same_length_dots
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_deny_by_default
- tests/unit/strata/test_facts.py::TestBuildFacts::test_builds_and_indexes_a_valid_model
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_counts_kept_violations
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 5/N of T-2359: apply ruff-format-only reformat to 13 test files.
No semantic changes; format-only diff.