+++
id = "01M35RZY81X9RWNXA2EB784R4A"
title = "REG008 burn-down: 24 check-coverage.yaml dispositions lack a real frob:enforces CHK-GATE edge"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5377"]
labels = ["milestone:0.534.0"]
scope = ["docs/design/registry/check-coverage.yaml", "src/frob/gates/_ratchet.py", "src/frob/gates/_claim_lint.py", "src/frob/gates/_coverage.py", "src/frob/gates/_guard_closure.py", "src/frob/gates/_sys_branch.py", "src/frob/gates/_pii_structural/__init__.py", "src/frob/gates/_inv.py", "src/frob/gates/_wrapper_drift.py", "src/frob/perf/_loop_variant.py", "src/frob/perf/_cache_effects.py", "src/frob/policy/__init__.py", "src/frob/vet/_scan.py", "src/frob/gates/_fix_engine_text.py", "src/frob/gates/__init__.py", "src/frob/strata/_selfconform_surface_rules.py", "src/frob/gates/_sys_provenance.py"]
+++

CI run 35819358270 (ubuntu/macos/windows); re-verified failing on dev tip 39b89ed091: tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml fails with 24 REG008 violations against docs/design/registry/check-coverage.yaml -- entries dispositioned handled_by:<RULE> whose rule has no real 'frob:enforces CHK-GATE-<RULE>' edge anywhere in code. Either add the missing frob:enforces directive at each rule's real enforcement site, or re-disposition the stale entries. Distinct from T-5179 (REG002: dispositions naming rules absent from the live registry) and T-3278 (stale ids vs known_gate_rule_ids) -- this is REG008 specifically, the enforces-edge check.
