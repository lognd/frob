+++
id = "01M4CTV1F6JTX89DKB1QKDYH7A"
title = "frob init --agent: write Claude Code settings for the project (MCP server, vet hook, permission allowlist for frob verbs) and an in-repo worktree option"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:44Z"
updated = "2026-10-08T04:02:44Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/frob-worktree/**", "docs/guides/**"]

[[acceptance]]
text = "Given frob init --agent, when run, then .claude/settings.json gains the frob MCP server and an allowlist for frob read verbs, idempotently"
bound = false

[[acceptance]]
text = "Given [worktree] root inside the repository, when frob work runs, then the worktree is created there and ignored by git"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md agent ergonomics: no generator for agent config; default worktree root ../repo-wt is outside the repository, which a sandboxed agent may not write. After ~MQ1NM4Q lands, the MCP entry points at frob serve.
