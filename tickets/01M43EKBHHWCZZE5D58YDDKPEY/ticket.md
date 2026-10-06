+++
id = "01M43EKBHHWCZZE5D58YDDKPEY"
title = "Share finding-record, source-resolver and text helpers between crunk-check and grimble-check"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "low"
reporter = "lognd"
created = "2026-10-04T12:35:40Z"
updated = "2026-10-06T04:33:22Z"
scope = ["crates/crunk-check/**", "crates/grimble-check/**", "crates/crunk/**", "crates/grimble/**"]
+++

found while working ~FYH8FGQ: sibling.rs (finding_json, sources_of) in crunk-check and grimble-check, and the lines_of/summary helpers in the crunk and grimble check verbs, are copies. Move them into a shared crate.
