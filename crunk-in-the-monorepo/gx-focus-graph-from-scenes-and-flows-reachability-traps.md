+++
id = "01M4CXRSYQQW9C6D7K2Q2ZC9QM"
title = "GX focus graph from scenes and flows: reachability, traps, default selection, wrap"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:49Z"
updated = "2026-10-22T07:50:51Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-layout/**", "crates/crunk-rules/**", "crates/crunk-scene/**"]

[[acceptance]]
text = "Given a menu scene with an unreachable button, when checked, then the GX focus rule fires naming it"
bound = true
+++

docs/design/crunk.md section 7.
