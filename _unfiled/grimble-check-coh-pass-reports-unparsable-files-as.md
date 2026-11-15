+++
id = "01M7EXW4Z73XY5VWK7F2Y6QSSP"
title = "grimble-check: COH pass reports unparsable files as Unresolved per COH rule"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "A syntactically broken source file yields Unresolved for each COH rule"
bound = false
+++

Audit: /home/logan/projects/frob-audit-grimble-crunk.md M7. coh_pass.rs:125-139,401-433 silently drops unparsable files. Remedy: return failures and emit one Unresolved per failed file per COH rule.
