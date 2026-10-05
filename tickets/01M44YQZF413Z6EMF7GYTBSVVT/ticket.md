+++
id = "01M44YQZF413Z6EMF7GYTBSVVT"
title = "frob init suggests the unity pack"
type = "story"
category = "todo"
priority = "low"
points = 2
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:03Z"
updated = "2026-10-05T02:37:03Z"
idempotency_key = "d94-init"
scope = ["crates/frob/src/init.rs", "crates/frob/src/first_run.rs", "crates/frob/src/config.rs", "crates/frob/tests/**", "docs/reference/cli/frob.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQXS4BXE0X07FBYR0STJ5"

[[acceptance]]
text = "Given a repository with ProjectSettings/ProjectVersion.txt, when frob init runs, then it prints the suggestion to enable the unity pack and does not change frob.toml"
bound = false

[[acceptance]]
text = "Given a repository with only a .csproj, when frob init runs, then no unity suggestion is printed"
bound = false

[[acceptance]]
text = "Given frob init run twice, when the second run completes, then the output and files are unchanged"
bound = false
+++

frob init (crates/frob/src/init.rs, first_run.rs, config.rs) detects ProjectSettings/ProjectVersion.txt and, when found, prints a suggestion with the exact config line to enable the unity pack and the detected editor version; it never enables it silently and is idempotent. Also suggests nothing when a .sln/.csproj-only repository is found (plain .NET needs no pack). Docs: docs/reference/cli/frob.md init section, docs/guides.
