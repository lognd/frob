+++
id = "01M5BJ2EVKDA4RYRDFRVHZ1FDQ"
title = "frob agent: agent-neutral sync/status/uninstall of tracked agent config (claude emitter first)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T02:25:58Z"
updated = "2026-10-20T03:06:49Z"
idempotency_key = "claude-sync-verb"
scope = ["crates/frob/src/claude_sync.rs", "crates/frob/src/claude_cmd.rs", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/frob/src/config.rs", "crates/frob/src/doctor.rs", "crates/frob/Cargo.toml", "crates/frob/tests/it/claude.rs", "crates/frob/tests/it/main.rs", "frob.toml", "docs/guides/claude-hooks.md", "crates/frob/src/agent", "crates/frob/src/agent_cmd.rs", "crates/frob/tests/it/agent.rs", "Cargo.lock"]

[[acceptance]]
text = "sync installs the manifest into an empty home, is idempotent, and uninstall preserves user additions"
bound = false

[[acceptance]]
text = "status reports drift (exit 1) and is surfaced by doctor"
bound = false

[[acceptance]]
text = "an Emitter trait lets a second (fake) agent be driven by the shared engine with no core change"
bound = false
+++

Add a noun-group verb 'frob claude' (same shape as lease/ticket/cycle) with subverbs: 'sync' (copy a MANAGED manifest from the repo into ~/.claude behind a do-not-edit banner, atomic temp+rename, backup, idempotent; also registers hooks in settings.json), 'status' (read-only drift report, exit 1 on drift; also surfaced as a frob doctor line), 'uninstall' (reverse only frob-owned files and settings entries, leave user additions untouched). Repo is canonical; never sync home -> repo. Reuse the idempotent/reversible settings.json install machinery from ~KHCKTS3 (do not duplicate it). Stale-source guard: refuse to sync a file whose worktree copy is behind base. Manifest is declared in frob.toml, not hardcoded. Hard tests: empty home, pre-existing user hooks, user edits after sync, uninstall preserves them, double sync byte-identical, drift detection. Prior art: old Python 'frob claude sync' (notes/v1/ops-and-integrations.md 6.4). Docs under docs/ in the same change.
