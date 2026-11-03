+++
id = "01M6G3BAB828TJEYKDKZA87WAH"
title = "ERR002 discarded-result burn-down: 426 findings"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-03T07:00:33Z"
updated = "2026-11-03T07:02:23Z"
scope = ["frob.toml", "changelog.d/**", "crates/frob-ledger/**", "crates/crunk-tokens/**", "crates/crunk/**", "crates/frob-evidence/**", "crates/frob-metrics/**", "crates/frob-mirror/**", "crates/frob-worktree/**"]
+++

Replace let _ = write!/writeln!/fs calls with explicit handling; delete [rules.ERR002] off table.
