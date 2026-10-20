+++
id = "01M4D6NHS19AGZS6NV6B077GY9"
title = "gob-symbols: persist the linked call graph and cache degraded files"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:27Z"
updated = "2026-10-08T07:29:27Z"
scope = ["changelog.d/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a warm check, when run, then degraded files are not re-folded and link_calls results are reused"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 8 (graph.rs link_calls 23-26 percent of ack and graph; pipeline.rs:236 re-folds about 283 degraded files per warm check).
