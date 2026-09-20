---
id: T-4276
title: update docs/guides/release.md for the T-4263 upload job split
state: done
kind: docs
origin: human
created: '2026-09-07'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:python -m pytest tests/unit/test_release_workflow_gate.py -q exit=0 sha256=bbaeb9b341c1
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4263 split release.yml's single 'upload' job into upload-frob-core / upload-strata-core / upload-frob (one job per distribution, each with its own GitHub Environment, to work around PyPI's pending-trusted-publisher collision). docs/guides/release.md still describes a single 'upload' job throughout (its job-graph description, the 'Proof: a normal push does not upload' section, the release-cut procedure's step list, and Decision 3/4 discussions) -- none of that is wrong in substance, but the job name it names no longer exists. Found while working T-4263, out of that ticket's docs/guides/release.md-EXCLUDED, .github/workflows/release.yml-only scope; not fixed there.