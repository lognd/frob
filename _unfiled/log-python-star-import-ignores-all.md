+++
id = "01M65FKM97K956PQS8M509EQA2"
title = "LOG: Python star import ignores __all__"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-17T05:47:13Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/output-atoms.md", "crates/grimble-check/tests/it/log_rules.rs", "docs/design/grimble/output-atoms.md", "changelog.d/01M65FKM97K956PQS8M509EQA2.fixed.md"]

[[acceptance]]
text = "Given a project module with a literal __all__, when another file star-imports it, then only the names listed in __all__ are bound"
bound = true
+++

found while working 01M64230T88F77RTBYS9M3CY3C: star imports bind every non-underscore export instead of honouring __all__.
