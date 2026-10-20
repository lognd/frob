+++
id = "01M4CXRSYQQW9C6D7K2Q2ZC9QM"
title = "GX focus graph from scenes and flows: reachability, traps, default selection, wrap"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-08T04:53:49Z"
updated = "2026-10-08T04:53:49Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-layout/**"]

[[acceptance]]
text = "Given a menu scene with an unreachable button, when checked, then the GX focus rule fires naming it"
bound = false
+++

docs/design/crunk.md section 7.
