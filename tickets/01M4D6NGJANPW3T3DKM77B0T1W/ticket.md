+++
id = "01M4D6NGJANPW3T3DKM77B0T1W"
title = "grimble-bind: cache per-file folds (shared ArtifactKey with frob) and build the U-term lazily"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:26Z"
updated = "2026-10-09T22:03:12Z"
labels = ["creates:crates/grimble-bind/tests/warm_cache.rs"]
scope = ["changelog.d/**", "crates/grimble-bind/Cargo.toml", "crates/grimble-bind/src/code.rs", "crates/grimble-bind/src/lib.rs", "crates/grimble-bind/src/live.rs", "crates/grimble-bind/src/edges.rs", "crates/grimble-bind/src/rules.rs", "crates/grimble-bind/src/relation.rs", "crates/grimble-bind/src/owner.rs", "crates/grimble-bind/src/directives.rs", "crates/grimble-bind/tests/warm_cache.rs", "Cargo.lock"]

[[acceptance]]
text = "Given a warm cache, when grimble ack and grimble check run, then no file is re-parsed (counter test) and peak memory drops"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 6: grimble ack 5.7-9 s and 1.35 GB.
