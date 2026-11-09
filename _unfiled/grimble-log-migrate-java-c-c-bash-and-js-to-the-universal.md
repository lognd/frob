+++
id = "01M6ZX0S7X0KVTGRPYEMV8PWVD"
title = "Grimble LOG: migrate Java, C, C#, Bash and JS to the universal model once adapters are precise"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T10:17:48Z"
updated = "2026-11-09T12:31:11Z"
scope = ["crates/grimble-check/src/log/pass.rs", "crates/grimble-check/src/log/universal.rs", "docs/design/grimble/output-atoms.md"]

[[acceptance]]
text = "JavaScript/TypeScript and C# calls resolve through U (C# using-globs and aliases) and the LOG cross-check does not double-report scanner hits"
bound = true

[[acceptance]]
text = "Java, C and Bash are deferred to follow-up tickets because their adapters record no call sites"
bound = true
+++
