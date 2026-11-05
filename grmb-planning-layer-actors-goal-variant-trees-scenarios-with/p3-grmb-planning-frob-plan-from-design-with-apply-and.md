+++
id = "01M6BYKXEJTGDTTA4X3P9A8KME"
title = "P3 grmb planning: frob plan --from-design with --apply and --findings"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FDBDC401KMNN4C12QTA3PK"
reporter = "lognd"
created = "2026-11-01T16:20:54Z"
updated = "2026-11-05T19:28:14Z"
labels = ["grimble", "no-story", "creates:crates/frob/tests/it/plan_from_design.rs"]
scope = ["crates/frob/src/plan_cmd.rs", "crates/frob/src/plan/**", "docs/design/cli.md", "changelog.d/**", "crates/frob/tests/it/plan_from_design.rs"]

[[links]]
kind = "blocked-by"
target = "01M6BYKR12BCNQ3P3BR3J3AR58"

[[acceptance]]
text = "Given the web example, when frob plan --from-design --apply runs twice, then the second run proposes no ticket and every created ticket carries implements design:<anchor> (parent AC1)"
bound = false

[[acceptance]]
text = "Given frob plan --from-design, when it proposes tickets, then goal maps to epic, scenario to story, and impl to task"
bound = false
+++

Child of ~2QTA3PK. Scope paths are best guess; implementer should widen the lease if the plan verb lives elsewhere. Work no-story.
