+++
id = "01M3AXSDC0Z8KZSSERWKB1CVEZ"
title = "CI regression sweep: export_golden, websec_rls_llm, TICK008, scaffold_dx, SELFAUDIT001, registry count"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6528"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/strata/test_export_golden.py", "tests/unit/test_websec_rls_llm.py", "tests/gates_suite/test_tick.py", "tests/system/test_scaffold_dx.py", "tests/system/test_frob_self_model.py", "src/frob/webapp/_websec_rls_llm.py", "src/frob/scaffold/data/types/python-tool/__main__.py.j2", "src/frob/scaffold/data/types/python-tool/tests/unit/test_logging.py.j2"]
+++

Found while draining CI run 36173008509 (dev 473cee7656). Six unrelated
small test regressions/drifts surfaced after syncing to a ~386-commit-old
dev tip; grouping into one ticket for triage/splitting rather than filing
six near-empty tickets under time pressure.

1. tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s and
   ::test_iam (ubuntu+macos) -- golden-file string mismatch (diff not
   visible in the truncated assertion; needs a local repro to see the
   actual diff).

2. tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc417_positive-WEBSEC417-True]
   (ubuntu+macos) -- AssertionError: () -- fixture expected a WEBSEC417
   finding and got none.

3. tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean
   (macos) -- live tickets.md now has TICK008 (unknown ledger field)
   violations; may overlap T-5527's TICK ledger burn-down scope but T-5527
   is filed against TICK006/015/003/004 specifically, not TICK008.

4. tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
   (macos) -- AssertionError: frob check .  [FAIL]  2 errors  5 warnings --
   the scaffolded python-tool template no longer passes `frob check`
   immediately after generation.

5. tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
   (macos) -- multiple new SELFAUDIT001 WARN findings: several self-audit
   "assume" entries across modules (SYS119) are template-identical after
   substituting the module name (weakness:CWE-502, CWE-639, CWE-78, CWE-79,
   CWE-89, CWE-918, CWE-94 families) -- each needs a module-owned assume
   naming its own concrete mechanism/evidence gap instead of a copy-paste.

6. tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
   (macos) -- assert 666 == 664 -- 2 more live gate rules than the registry
   file's declared count; likely the same SQL/LAUNCH landing gap tracked
   separately (see the SQL/LAUNCH wiring ticket) but flagged here in case
   it is not.

Proposed handling: split each numbered item into its own ticket once
triaged; none looked small/safe enough to blind-fix without a local repro
in the time available for this drain.
