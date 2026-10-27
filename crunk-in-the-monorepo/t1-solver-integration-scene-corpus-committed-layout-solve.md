+++
id = "01M4CXREV41PNTSYVFFG2AXW7M"
title = "T1 solver integration: scene corpus, committed layout-solve baselines, T1 rules run from the solver output in CI"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:45Z"
updated = "2026-10-27T00:41:55Z"
scope = ["changelog.d/**", "crates/crunk-layout/**"]

[[links]]
kind = "blocked-by"
target = "01M5XCWYB9M2YSJ5EGABMREX1B"

[[acceptance]]
text = "Given the scene corpus, when solved twice, then outputs are byte-identical and match committed baselines"
bound = false

[[acceptance]]
text = "Given the corpus, when LAYOUT, RESP and GX focus rules run at T1 in CI with no browser, then findings come from solver output and match committed baselines"
bound = false
+++

docs/design/crunk.md section 3.
