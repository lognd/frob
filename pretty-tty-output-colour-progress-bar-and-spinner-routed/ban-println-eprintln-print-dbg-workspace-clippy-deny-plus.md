+++
id = "01M5XMR625ABZ4HX19EJ1PTXPF"
title = "Ban println/eprintln/print/dbg: workspace clippy deny plus remove current call sites"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T02:59:06Z"
updated = "2026-10-27T03:40:02Z"
scope = ["Cargo.toml", "clippy.toml", "crates/frob/src/lease_cmd.rs", "crates/gob-exec/src/prereq.rs", "crates/gob-plan/**", "crates/gob-testsupport/**", "crates/frob-check/benches/full_check.rs", "crates/gob-packs/benches/b2_disk_vs_compiled.rs", "crates/crunk-check/clippy.toml", "crates/frob-check/clippy.toml", "crates/gob-check/clippy.toml", "crates/gob-rules/clippy.toml", "crates/grimble-check/clippy.toml", "crates/gob-symbols/tests/it/web_corpus.rs", "crates/crunk-tailwind/tests/runtime.rs", "CONTRIBUTING.md", "crates/frob/build.rs", "docs/design/architecture.md", "docs/guides/agents.md"]

[[acceptance]]
text = "workspace lints deny clippy::print_stdout, print_stderr and dbg_macro; build scripts, benches and tests are explicitly allowed; lease_cmd.rs and prereq.rs log through gob-log instead"
bound = false

[[acceptance]]
text = "gob-plan and gob-testsupport print sites are routed through gob-log or the presenter, or allowed with a recorded reason"
bound = true
+++

Audit 2026-10-26: gob-log's docs say never println! outside the renderer crate but nothing enforces it. Non-test, non-bench sites today: crates/frob/src/lease_cmd.rs:113 (eprintln), crates/gob-exec/src/prereq.rs:19 (eprintln), plus gob-plan and gob-testsupport; build.rs println is the cargo protocol and stays allowed.
