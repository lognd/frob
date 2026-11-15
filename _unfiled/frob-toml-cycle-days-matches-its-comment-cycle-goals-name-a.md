+++
id = "01M7EXQZGM18986N7B4K0Q15HB"
title = "frob.toml cycle_days matches its comment; cycle goals name a criterion"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:19:04Z"
updated = "2026-11-15T06:19:04Z"
labels = ["no-story"]

[[acceptance]]
text = "Comment and value agree"
bound = false
+++

Source: frob-audit-meta.md L3. Evidence: frob.toml:178 cycle_days = 2 vs comment. Remedy: fix the comment or value and require a criterion in cycle goals. Files: frob.toml.
