---
id: T-3041
title: 13 live-repo self-conformance tests fail (repo currently non-zero on multiple
  gates)
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/
- tests/system/test_frob_self_model.py
- tests/golden/frob_export_iam.json
- tests/golden/frob_export_k8s.yaml
- tests/golden/frob_export_seccomp.json
scope_breadth_ack: true
scope_breadth_ack_reason: T-3041 is a triage umbrella over the repo's own self-conformance
  test family (13 tests spanning many gate modules under tests/unit/strata/ + test_frob_self_model.py);
  the broad glob is the honest scope for a triage ticket whose job is categorizing
  findings across many files, not editing one narrow package.
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/golden/frob_export_iam.json
  reason: test_export_golden.py (in scope) asserts these fixtures byte-match design/frob.strata's
    real export -- T-3029 legitimately changed that model (new narrative node/flows/may-via),
    so the golden files are stale-by-construction and must be regenerated as part
    of fixing the in-scope test
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/golden/frob_export_k8s.yaml
  reason: test_export_golden.py (in scope) asserts these fixtures byte-match design/frob.strata's
    real export -- T-3029 legitimately changed that model (new narrative node/flows/may-via),
    so the golden files are stale-by-construction and must be regenerated as part
    of fixing the in-scope test
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/golden/frob_export_seccomp.json
  reason: test_export_golden.py (in scope) asserts these fixtures byte-match design/frob.strata's
    real export -- T-3029 legitimately changed that model (new narrative node/flows/may-via),
    so the golden files are stale-by-construction and must be regenerated as part
    of fixing the in-scope test
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Linux full-suite triage (T-2992): 13 tests fail that all share ONE
distinctive shape: they assert the repo's OWN gate/registry/self-model
output is currently CLEAN (zero violations) when measured against this
live checkout's real state (docstrings say "against live repo design",
"real repo", "unrestricted scan is clean", etc.) -- they are not testing
a synthetic fixture, they are testing THIS repo's actual current
gate-clean status.

This matches what an earlier `frob check --ticket T-3015 --budget 480`
run in this same worktree already showed repo-wide (unrelated to T-3015
or T-2992's own scope): non-zero FAIL counts on gate:DOC, gate:DRIFT,
gate:PRE, gate:REF, gate:REG, gate:SCOPE, gate:TEST, gate:TICK,
gate:WAIVE, gate:ARCH, gate:LARGE, gate:PII, gate:SEC, gate:SELFAUDIT,
gate:SYS (103 errors / 175 warnings on the gates-fast/gates-native/
gates-security/lint/static budget alone). These 13 tests are almost
certainly just faithfully reporting that same non-zero state through a
different lens (a pytest assertion instead of a `frob check` exit code),
NOT a new Linux-specific defect and NOT something T-2980/T-2991's hang
fix introduced.

FAILING (13):
  tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
  tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
  tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
  tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
  tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
  tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean@selfconform-full-repo-scan
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant@selfconform-full-repo-scan
  tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design

TRIAGE NEEDED (not done here): these tests being ratchets against the
live repo state means they may ALREADY be flagged elsewhere (fleet
dashboards, other tickets tracking the non-zero gate counts) -- before
treating this as 13 separate defects, check whether the underlying
non-zero gate findings each already have an owning ticket; if so this
ticket's job is just to point at them, not duplicate. If some of these
13 assertions are NEWLY non-zero (a real regression, not pre-existing
debt), that needs isolating per-assertion by diffing against the last
known-good measurement.