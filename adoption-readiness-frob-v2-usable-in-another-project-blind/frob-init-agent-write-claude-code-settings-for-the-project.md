+++
id = "01M4CTV1F6JTX89DKB1QKDYH7A"
title = "frob init --agent: write Claude Code settings for the project (MCP server, vet hook, permission allowlist for frob verbs) and an in-repo worktree option"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:44Z"
updated = "2026-10-22T02:48:33Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/frob-worktree/**", "docs/guides/**"]

[[acceptance]]
text = "Given frob init --agent, when run, then .claude/settings.json gains the frob MCP server and an allowlist for frob read verbs, idempotently"
bound = false

[[acceptance]]
text = "Given [worktree] root inside the repository, when frob work runs, then the worktree is created there and ignored by git"
bound = false

[[acceptance]]
text = "Given an existing settings.json with unrelated keys and an allow list, when frob init --agent runs, then those are preserved and the frob server and read allowlist are merged"
bound = false

[[acceptance]]
text = "Given settings already configured, when frob init --agent runs again, then the file is byte-identical and no entry is duplicated"
bound = false

[[acceptance]]
text = "Given malformed or wrongly shaped settings.json, when frob init --agent runs, then it is refused and the file is left untouched"
bound = false

[[acceptance]]
text = "Given a worktree dir inside the repo, when frob work creates a worktree, then git ignores it with exactly one line and an existing .gitignore entry is not duplicated"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md agent ergonomics: no generator for agent config; default worktree root ../repo-wt is outside the repository, which a sandboxed agent may not write. After ~MQ1NM4Q lands, the MCP entry points at frob serve.
