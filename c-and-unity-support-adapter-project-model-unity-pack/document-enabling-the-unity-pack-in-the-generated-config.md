+++
id = "01M5F8MNTSHY6YQSRAMC8624FR"
title = "document enabling the unity pack in the generated config reference"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T12:58:07Z"
updated = "2026-11-11T22:43:26Z"
scope = ["crates/grimble-check/src/config.rs", "docs/reference/config/frob.md", "changelog.d/01M5F8MNTSHY6YQSRAMC8624FR.changed.md", "docs/schemas/config.json", "docs/README.md"]

[[acceptance]]
text = 'The generated config reference documents that packs.enabled = ["unity"] opts in to the Unity pack'
bound = true
+++

found while working ~YR0STJ5: docs/reference/config.md is generated from crates/grimble-check/src/config.rs doc comments (out of scope)
