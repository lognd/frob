+++
id = "01M4HEMDB8A1X1RQFNVJB1G32M"
title = "grimble check --summary: a compact JSON summary (counts per rule and severity, per-node CAP cell counts, digests) suitable as file evidence under frob's size cap"
type = "story"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T23:05:36Z"
updated = "2026-10-09T23:05:36Z"
labels = ["grimble", "adoption:logand-app"]
scope = ["crates/grimble/src/**", "crates/grimble-check/src/**", "changelog.d/**"]

[[acceptance]]
text = "Given a large model, when grimble check --summary --json runs, then the output is under 64 KB, lists counts per rule and severity and per-node capability cells, and carries the compute digest of the full document"
bound = false
+++

logand.app-v2: a 5.5 MB grimble check --json committed as file evidence hit frob's size cap.
