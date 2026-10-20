+++
id = "01M5BJ2EVKDA4RYRDFRVHZ1FDQ"
title = "frob agent: agent-neutral sync/status/uninstall of tracked agent config (claude emitter first)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T02:25:58Z"
updated = "2026-10-20T03:14:00Z"
idempotency_key = "claude-sync-verb"
scope = ["crates/frob/src/claude_sync.rs", "crates/frob/src/claude_cmd.rs", "crates/frob/src/lib.rs", "crates/frob/src/product.rs", "crates/frob/src/config.rs", "crates/frob/src/doctor.rs", "crates/frob/Cargo.toml", "crates/frob/tests/it/claude.rs", "crates/frob/tests/it/main.rs", "frob.toml", "docs/guides/claude-hooks.md", "crates/frob/src/agent", "crates/frob/src/agent_cmd.rs", "crates/frob/tests/it/agent.rs", "Cargo.lock", "crates/frob/src/agent/mod.rs", "crates/frob/src/agent/engine.rs"]

[[acceptance]]
text = "sync installs the manifest into an empty home, is idempotent, and uninstall preserves user additions"
bound = true

[[acceptance]]
text = "status reports drift (exit 1) and is surfaced by doctor"
bound = true

[[acceptance]]
text = "an Emitter trait lets a second (fake) agent be driven by the shared engine with no core change"
bound = true
+++

Agent-neutral noun group 'frob agent' with sync, status, uninstall, each taking --agent claude|all. Each agent is an Emitter (target paths, render, register/unregister); a shared engine owns atomic writes, backups, banner, idempotence, drift detection, reversibility (frob-owned only) and the stale guard. Manifest declared in frob.toml [agent]. Claude is the only emitter now; adding another is one module plus one line in emitters(). Docs: docs/guides/claude-hooks.md.
