+++
id = "01M5BN07NSGG64QPAH5HWNF3RV"
title = "frob agent: preserve settings.json key order on write"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T03:17:10Z"
updated = "2026-11-09T07:24:34Z"
scope = ["crates/frob/Cargo.toml", "crates/frob/tests/it/agent_install.rs", "crates/frob/src/agent/claude.rs", "Cargo.lock", "changelog.d/01KZHWNF3RV00000000000000.fixed.md", "docs/guides/hooks.md", "changelog.d/01M5BN07NSGG64QPAH5HWNF3RV.fixed.md", "docs/schemas/**", "crates/gob-dev/src/render/mod.rs"]

[[acceptance]]
text = "frob agent keeps the existing settings.json key order on write"
bound = true
+++

serde_json without preserve_order alphabetizes keys when the claude emitter rewrites settings.json. Found while working ~VHZ1FDQ.
