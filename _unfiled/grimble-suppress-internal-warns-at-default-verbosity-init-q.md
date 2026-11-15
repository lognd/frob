+++
id = "01M7EXVKWWGF5CJJ9QFXN14A1R"
title = "grimble: suppress internal WARNs at default verbosity; init -q prints no JSON envelope"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:03Z"
updated = "2026-11-15T06:21:03Z"
labels = ["no-story"]

[[acceptance]]
text = "Default run prints no internal tracing WARN"
bound = false

[[acceptance]]
text = "init -q piped prints nothing but the exit code"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md L8. gob_check::required DEAD001, gob_check::repo SYS015 and CODEOWNERS x3 WARNs leak at default verbosity; init -q still prints the full JSON envelope when piped.
