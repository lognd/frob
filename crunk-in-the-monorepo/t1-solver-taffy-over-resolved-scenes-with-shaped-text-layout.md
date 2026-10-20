+++
id = "01M4CXREV41PNTSYVFFG2AXW7M"
title = "T1 solver: taffy over resolved scenes with shaped text, layout-solve JSON (boxes, overflow, focus order) and committed baselines"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:45Z"
updated = "2026-10-08T04:53:45Z"
scope = ["changelog.d/**", "crates/crunk-layout/**"]

[[acceptance]]
text = "Given the scene corpus, when solved twice, then outputs are byte-identical and match committed baselines"
bound = false
+++

docs/design/crunk.md section 3.
