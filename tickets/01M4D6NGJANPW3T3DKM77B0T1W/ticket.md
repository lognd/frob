+++
id = "01M4D6NGJANPW3T3DKM77B0T1W"
title = "grimble-bind: cache per-file folds (shared ArtifactKey with frob) and build the U-term lazily"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:26Z"
updated = "2026-10-08T07:29:26Z"
scope = ["changelog.d/**", "crates/grimble-bind/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given a warm cache, when grimble ack and grimble check run, then no file is re-parsed (counter test) and peak memory drops"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 6: grimble ack 5.7-9 s and 1.35 GB.
