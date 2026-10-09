+++
id = "01M4GKDSGA7ZSF99T7M5S319B4"
title = "Tool stages and evidence in fresh worktrees: uv run --no-sync fails with no .venv, vitest provider lacks node_modules/.bin on PATH, E-ATTEST-NOT-HUMAN fallback unclear"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T15:10:08Z"
updated = "2026-10-09T15:10:08Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-check/**", "crates/frob-evidence/**", "crates/frob-land/**", "changelog.d/**"]

[[acceptance]]
text = "Given a fresh ticket worktree or land base checkout without .venv, when a uv-run tool stage runs, then frob syncs the environment first (or the stage reports Unresolved with the remedy), never a red gate"
bound = false

[[acceptance]]
text = "Given a vitest project, when the vitest evidence provider runs, then node_modules/.bin is on PATH"
bound = false

[[acceptance]]
text = "Given an agent actor, when attestation evidence is refused, then the message names the agent-usable providers to use instead"
bound = false
+++

logand.app-v2 F-558.
