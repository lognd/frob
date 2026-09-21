---
id: T-3865
title: 'waiver-hygiene family (WAIVE004/010) burn-down: 265 unwaived findings'
state: queued
kind: bug
origin: agent
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: v0.541.0
runs_last: false
milestone: v0.541.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_waive_gate.py::TestWaive010Violations::test_plain_permanent_reason_does_not_warn
- tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription::test_relative_markdown_image_in_declared_readme_fires_error
- tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3844 burn-down: this rule/cluster (WAIVE004,WAIVE010) carried 265 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for WAIVE004,WAIVE010 to zero (real fixes and/or reasoned frob:waive entries), then promote WAIVE004,WAIVE010 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.