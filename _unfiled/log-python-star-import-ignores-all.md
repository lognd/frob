+++
id = "01M65FKM97K956PQS8M509EQA2"
title = "LOG: Python star import ignores __all__"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-17T03:07:43Z"
labels = ["no-story", "good-first"]
scope = ["crates/grimble-check/src/log/**", "docs/design/output-atoms.md"]
+++

found while working 01M64230T88F77RTBYS9M3CY3C: star imports bind every non-underscore export instead of honouring __all__.
