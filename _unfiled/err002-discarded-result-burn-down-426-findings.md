+++
id = "01M6G3BAB828TJEYKDKZA87WAH"
title = "ERR002 discarded-result burn-down: 426 findings"
type = "chore"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-11-03T07:00:33Z"
updated = "2026-11-03T07:18:41Z"
scope = ["frob.toml", "changelog.d/**", "crates/frob-ledger/**", "crates/crunk-tokens/**", "crates/crunk/**", "crates/frob-evidence/**", "crates/frob-metrics/**", "crates/frob-mirror/**", "crates/frob-worktree/**", "crates/gob-dev/**", "crates/gob-fix/**", "crates/gob-git/**", "crates/gob-log/**", "crates/gob-mdtest/**", "crates/gob-packs/**", "crates/gob-serve/**", "crates/gob-trust/**", "crates/grimble-capabilities/**", "crates/grimble-check/**", "crates/grimble-model/**", "crates/grimble/**", "changelog.d/01M6G3BAB828TJEYKDKZA87WAH.*.md"]
+++

Replace let _ = write!/writeln!/fs calls with explicit handling; delete [rules.ERR002] off table.
