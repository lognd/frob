---
id: T-4415
title: CI as the declared unscoped-authority full sweep
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4414
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- docs
- tests/unit/test_ci_self_gate_unscoped.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ci_self_gate_unscoped.py
  reason: AC1/AC2 workflow-shape tests, matching test_release_workflow_gate.py's pattern
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_documented_as_unscoped_authority
- tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split
- tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_reuses_finding_filing_path_not_a_new_implementation
- tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_attributes_to_a_commit_range
designated_repro_test: null
acceptance:
- text: GIVEN ci.yml's self-gate job WHEN it runs THEN it is the declared, documented
    full-sweep (unscoped) source of truth for the repo, distinct from any per-land
    scoped check
  evidence:
  - tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateIsUnscoped::test_self_gate_documented_as_unscoped_authority
- text: GIVEN CI reports red on an unscoped rule WHEN the failure is processed THEN
    a ticket is filed attributed to the batch, reusing the post-land attribution engine
    (T-1690)
  evidence:
  - tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_reuses_finding_filing_path_not_a_new_implementation
  - tests/unit/test_ci_self_gate_unscoped.py::TestSelfGateRegressionFiling::test_filing_step_attributes_to_a_commit_range
- text: GIVEN a developer reads docs/ WHEN they look for the land vs CI split THEN
    a documented statement says land proves the diff, CI proves the repo
  evidence:
  - tests/unit/test_ci_self_gate_unscoped.py::TestLandVsCiDocumentedSplit::test_both_doc_homes_state_the_split
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11): CI/CD is the single source of full-suite/full-gate runs; land proves only the diff. Make ci.yml's self-gate the declared unscoped-authority run, wire its red findings on unscoped rules to file tickets attributed to the batch (reusing T-1690's post-land attribution engine), and document the land/CI split in docs/.