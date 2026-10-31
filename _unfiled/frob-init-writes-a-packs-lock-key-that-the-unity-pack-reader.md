+++
id = "01M67XWWJETR3T2Z23J2439BMN"
title = "frob init writes a [packs] lock key that the unity pack reader rejects"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-31T02:51:22Z"
updated = "2026-10-31T02:51:22Z"
scope = ["crates/frob-obligations/src/unity.rs"]
+++

found while working ~RJFEASS: a fresh frob init writes frob.toml with [packs] lock = "grimble.packs.lock" (default from grimble-check config). The frob-obligations unity reader parses [packs] with deny_unknown_fields and expects enabled or enable, so every frob ticket or check run in a fresh repo logs PACK005 'unknown field lock' and treats the unity pack as disabled. Repro: git init a repo, frob init, frob ticket list. Writer side: crates/grimble-check/src/config.rs:46.
