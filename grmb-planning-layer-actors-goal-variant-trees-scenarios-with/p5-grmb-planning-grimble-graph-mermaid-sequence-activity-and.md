+++
id = "01M4FDBG95B8D1NERFERXC0PXF"
title = "P5 grmb planning: grimble graph --mermaid sequence, activity and use-case diagrams"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T04:04:47Z"
updated = "2026-10-28T12:57:42Z"
labels = ["grimble", "no-story"]
scope = ["crates/grimble/**", "crates/grimble-check/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FDBERB4M7E9RG2HD4J3YZ2"

[[acceptance]]
text = "Given both worked examples, when grimble graph --mermaid runs, then insta snapshots of the sequence, activity and use-case diagrams are stable and every arm and retry bound appears"
bound = false
+++

grmb-planning.md 11, row P5. Per scenario a sequence diagram (actors and nodes as lifelines, Succ pairs as messages, arms as alt, retry as loop) and an activity diagram; per system a use-case diagram.

no-story: internal engineering task in grimble; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
