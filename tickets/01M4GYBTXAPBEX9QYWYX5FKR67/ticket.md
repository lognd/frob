+++
id = "01M4GYBTXAPBEX9QYWYX5FKR67"
title = "may grants carry a reason (because= or ticket=) and grimble status reports grant count, breadth and their change since the lock (grant ratchet)"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T18:21:18Z"
updated = "2026-10-09T18:21:18Z"
labels = ["grimble", "adoption:logand-app"]
scope = ["crates/grimble*/**", "docs/design/grmb-spec.md", "changelog.d/**"]

[[acceptance]]
text = "Given a may clause without because= or ticket=, when grimble check runs, then an MDL finding asks for the reason"
bound = false

[[acceptance]]
text = "Given grants added or widened since grimble.lock, when grimble status runs, then it reports grant count, selector breadth (files matched) per node and the delta, and a widening is listed by name"
bound = false
+++

logand model: 57 grant lines, none with a rationale in the model; reasons live only in v1 commit messages and tickets.
