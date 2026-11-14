+++
id = "01M7CV0ZXC6PES5GJ3PAB09FA1"
title = "Expand {file} token for per-file tool stages so clang-format def runs"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-14T10:53:05Z"
updated = "2026-11-14T17:13:11Z"
labels = ["no-story"]
scope = ["crates/gob-check/**", "crates/gob-check/src/pipeline.rs"]

[[acceptance]]
text = "A tool stage with a {file} arg runs once per matching tracked file as ./path, scoped to the scope files when given"
bound = true
+++

found while working ~KSSQVNQ: expand_file is dead code, so the clang-format def passes a literal {file}
