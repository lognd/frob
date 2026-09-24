---
id: T-5469
title: strata export golden fixtures (k8s, iam) stale against real export shape
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing (ubuntu +
macos, both node ids in one file/fixture family):
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam

Both diff a rendered strata export against a golden fixture. The k8s diff
shows "app: narrative" replacing an "app: registry_model..." label plus a
new NetworkPolicy ingress rule block ("- from: - podSelector: matchLabels:
..."), consistent with a real strata export shape change (a renamed app
label and/or a new ingress/egress rule) that the golden fixtures were
never regenerated for.

Fix: confirm whether the export-shape change is intentional (check its own
land history) -- if intentional, regenerate both k8s and iam goldens
against today's real export; if not, this is a regression in the exporter
itself and the exporter needs fixing instead of the goldens.
