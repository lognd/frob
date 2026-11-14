+++
id = "01M7CV0ZXC6PES5GJ3PAB09FA1"
title = "Expand {file} token for per-file tool stages so clang-format def runs"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T10:53:05Z"
updated = "2026-11-14T11:03:12Z"
labels = ["no-story"]
scope = ["crates/gob-check/**"]
+++

found while working ~KSSQVNQ: expand_file is dead code, so the clang-format def passes a literal {file}
