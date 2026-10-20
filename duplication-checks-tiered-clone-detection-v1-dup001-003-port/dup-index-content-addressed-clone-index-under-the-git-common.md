+++
id = "01M4P0SXCZQTRS8W10VXJ1W4P0"
title = "dup index: content-addressed clone index under the git common dir, incremental, fail closed (DUP003)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-10-11T17:40:09Z"

[[acceptance]]
text = "Index is built once and updated only for changed files"
bound = false

[[acceptance]]
text = "Missing or corrupt index fails closed with DUP003 and a rebuild hint"
bound = false

[[acceptance]]
text = "Shared by all worktrees"
bound = false
+++
