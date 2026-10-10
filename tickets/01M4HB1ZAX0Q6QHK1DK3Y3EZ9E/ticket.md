+++
id = "01M4HB1ZAX0Q6QHK1DK3Y3EZ9E"
title = "gob-ir/gob-symbols: serialize Term and ScopeGraph so grimble-bind can cache folded terms"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T22:03:06Z"
updated = "2026-10-09T22:03:06Z"
scope = ["crates/gob-ir/**", "crates/gob-symbols/src/pipeline.rs", "crates/grimble-bind/src/code.rs"]

[[acceptance]]
text = "Given a warm cache, when grimble ack --dry-run --all runs on this repository, then no adapter parse occurs (counter test) and user CPU drops by at least 50 percent"
bound = false
+++

found while working ~77B0T1W: grimble-bind now caches FileSymbols and a per-file summary, but selectors need the U term of about 950 files on this repo, folded on demand (user CPU 28 s to 25 s, RSS 1.64 to 1.57 GB for grimble ack --dry-run --all). Caching Term and ScopeGraph (postcard, same ArtifactKey plus a term schema version) removes those parses.
