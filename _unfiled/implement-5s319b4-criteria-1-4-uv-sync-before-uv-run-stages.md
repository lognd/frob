+++
id = "01M5MMEYZXZW5MNXSTMZ9F7SRN"
title = "Implement 5S319B4 criteria 1-4: uv sync before uv-run stages, vitest PATH, attestation message, per-worktree venv"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-23T15:00:54Z"
updated = "2026-10-23T19:37:36Z"
scope = ["crates/gob-check/src/tools.rs", "crates/frob-worktree/**", "crates/frob-evidence/**", "changelog.d/**"]

[[acceptance]]
text = "Given a fresh ticket worktree or land base checkout without .venv, when a uv-run tool stage runs, then frob syncs the environment first (or the stage reports Unresolved with the remedy), never a red gate"
bound = true

[[acceptance]]
text = "Given a vitest project, when the vitest evidence provider runs, then node_modules/.bin is on PATH"
bound = false

[[acceptance]]
text = "Given an agent actor, when attestation evidence is refused, then the message names the agent-usable providers"
bound = false

[[acceptance]]
text = "Given a uv/venv Python project whose shared .venv is an editable install of the main checkout, when frob work creates the worktree, then tests in that worktree import the worktree's code"
bound = false
+++

Ticket 5S319B4 closed with criteria 1-4 marked bound by a workspace-wide nextest command, but the code is absent on experimental (no uv --no-sync handling, no python_env.rs, no vitest PATH handling). Only criterion 5 (requires / [check] setup) was implemented.
