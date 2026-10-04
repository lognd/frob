+++
id = "01M38BCNN5SC8PF4KPSVF2FAYY"
title = "TIER002: resolve frob:verifies against the strata V-model graph"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-5797"]
labels = ["v1-cluster:B3d", "triage:accepted"]
scope = ["src/frob/gates/_tickets_gate.py"]
+++

found while working T-5763 (B2, ledger-tiers): TIER002's user_story branch currently only checks a frob:verifies <target> directive is PRESENT in the story body; it does not resolve <target> against the real strata V-model graph (verifies edges, customer-level artifact nodes) the way TIER002's quality_objective branch resolves frob:invariant against the real loaded invariant set. This graph-validated follow-up closes that gap.
