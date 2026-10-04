+++
id = "01M38BCNBG2088RGP3XJGPP69S"
title = "Widen a11y_gate hook contract so _locate_statement_page gets a repo root"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:01:14Z"
aliases = ["T-5488"]
labels = ["v1-cluster:B2", "area:crunk"]
scope = ["src/frob/webapp/_a11y_statement.py"]
+++

T-5454's done report documents _locate_statement_page(root, frameworks) as a deliberate known gap: a11y_gate's per-file hook contract (T-5323) has no reliable repo root to pass it, so it stays unwired into any production caller, kept only for direct tests. Widen the hook contract (or give per-file hooks a memoized repo-root handle) so this can wire in for real. Found while working T-5470 (its WIRE001 waiver named T-5454, now done, as the follow-up -- repointed here).
