+++
id = "01M7EXQZZ5QGF8B2ZBP0KWVKBA"
title = "LOG001: declarable CLI output sinks instead of defers"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:05Z"
updated = "2026-11-15T06:19:05Z"
labels = ["no-story"]

[[acceptance]]
text = "A declared sink is not flagged (test)"
bound = false
+++

Source: frob-audit-meta.md L4, follow-up to ~72KW077. Remedy: a config list of output-sink fns exempt from LOG001. Files: LOG001 rule, frob.toml.
