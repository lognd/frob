+++
id = "01M4GK42XB93XT5TFDQDRQ36JC"
title = "grimble-model directive check_args still rejects v1 ticket aliases (T-####) on frob:ticket and frob:todo, disagreeing with gob-directives after ~KP5659Y"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T15:04:50Z"
updated = "2026-10-10T19:30:00Z"
labels = ["adoption:logand-app"]
scope = ["crates/grimble-model/src/directive.rs", "changelog.d/**", "crates/gob-directives/src/lib.rs"]

[[acceptance]]
text = "Given a .grmb file with // frob:ticket T-0042, when grimble check runs, then no DSL002 or abbreviation finding fires, matching frob's directive scanner"
bound = true
+++
