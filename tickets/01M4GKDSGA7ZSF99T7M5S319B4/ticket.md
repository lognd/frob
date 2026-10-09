+++
id = "01M4GKDSGA7ZSF99T7M5S319B4"
title = "Tool stages and evidence in fresh worktrees: uv run --no-sync fails with no .venv, vitest provider lacks node_modules/.bin on PATH, E-ATTEST-NOT-HUMAN fallback unclear"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T15:10:08Z"
updated = "2026-10-09T22:43:42Z"
labels = ["adoption:logand-app", "creates:crates/frob-worktree/tests/python_env.rs"]
scope = ["changelog.d/**", "crates/gob-check/src/tools.rs", "crates/frob-worktree/src/work.rs", "crates/frob-worktree/tests/python_env.rs", "docs/design/cicd.md"]

[[acceptance]]
text = "Given a fresh ticket worktree or land base checkout without .venv, when a uv-run tool stage runs, then frob syncs the environment first (or the stage reports Unresolved with the remedy), never a red gate"
bound = false

[[acceptance]]
text = "Given a vitest project, when the vitest evidence provider runs, then node_modules/.bin is on PATH"
bound = false

[[acceptance]]
text = "Given an agent actor, when attestation evidence is refused, then the message names the agent-usable providers to use instead"
bound = false

[[acceptance]]
text = "Given a ticket worktree of a uv/venv Python project whose shared .venv is an editable install of the main checkout, when frob work creates the worktree, then tests in that worktree import the worktree's code (a per-worktree venv or an editable re-point), never the main checkout's (logand F-560)"
bound = false

[[acceptance]]
text = 'Given a tool stage that needs gitignored build output (e.g. a wasm-pack package or a generated setup file), when it declares requires = ["<command>"] or the repository declares [check] setup steps, then land checkouts and fresh worktrees run them before the stage, and a stage whose prerequisite failed reports Unresolved naming the prerequisite instead of passing failures as pre-existing (logand F-567)'
bound = false
+++

logand.app-v2 F-558.
