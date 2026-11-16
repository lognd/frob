+++
id = "01M6607PD368825RS2ZYKS9CCX"
title = "CAP: drop edge-guess May uses duplicating a resolved aliased call"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T08:53:44Z"
updated = "2026-11-16T21:01:31Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/caps/**"]

[[acceptance]]
text = "Given a Python source calling i.open(p) where i is an aliased module import, when grimble check scans it, then only the one certain use is reported and no extra May use duplicates it, proven by a test in crates/grimble-bind/src/caps.rs."
bound = false
+++

found while working ~MM08TTF: i.open with i a module alias adds May uses beside the certain one
