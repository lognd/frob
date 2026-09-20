---
id: T-4496
title: 'Post-alpha dev-branch workflow: land onto dev, CI on dev, re-enable dev version
  bump'
state: done
kind: feature
origin: agent
created: '2026-09-15'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- .github/workflows/ci.yml
- docs/guides/release.md
- tests/unit/test_dev_branch_workflow.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_dev_branch_workflow.py
  reason: evidence test asserting the dev-branch config and CI trigger shape
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/test_dev_branch_workflow.py::test_land_target_is_dev
- tests/unit/test_dev_branch_workflow.py::test_ci_runs_on_dev_and_main
- tests/unit/test_dev_branch_workflow.py::test_dev_version_bump_is_on
designated_repro_test: null
acceptance:
- text: GIVEN the root checkout on dev WHEN frob ticket land runs without --onto THEN
    it publishes onto dev (ticket_land_branch = dev in pyproject)
  evidence:
  - tests/unit/test_dev_branch_workflow.py::test_land_target_is_dev
- text: GIVEN a push to dev WHEN ci.yml triggers THEN the full CI matrix runs on dev
    as it does on main
  evidence:
  - tests/unit/test_dev_branch_workflow.py::test_ci_runs_on_dev_and_main
- text: GIVEN a land on dev WHEN it completes THEN the per-land PEP 440 dev version
    bump is applied again (dev_version_bump = true)
  evidence:
  - tests/unit/test_dev_branch_workflow.py::test_dev_version_bump_is_on
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-15: alpha 0.531.0 is released; develop on a non-main branch, keep main green, merge per sprint release. main stays frozen at the released green commit; dev is the land target for sprint v0.532.0; dev is fast-forwarded into main once the sprint's CI run on dev is green and the version is bumped. Adds ticket_land_branch = dev and dev_version_bump = true under [tool.frob], adds dev to ci.yml push branches, and documents the branch flow in docs/guides/release.md.