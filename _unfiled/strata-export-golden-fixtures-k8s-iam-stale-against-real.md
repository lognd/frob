+++
id = "01M38BCNAXSSRHGE4PT8NWERTP"
title = "strata export golden fixtures (k8s, iam) stale against real export shape"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5469"]
labels = ["milestone:v0.534.0"]
scope = ["tests/golden/frob_export_k8s.yaml", "tests/golden/frob_export_iam.json"]
+++

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
