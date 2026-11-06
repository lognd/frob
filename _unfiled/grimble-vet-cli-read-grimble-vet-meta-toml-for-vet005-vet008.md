+++
id = "01M6R4YNSHJDGT9WHHDW94XBBH"
title = "grimble vet CLI: read .grimble/vet-meta.toml for VET005-VET008"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-11-06T10:02:32Z"
updated = "2026-11-06T10:02:32Z"
labels = ["no-story"]
+++

vet_cmd.rs does not read vet-meta.toml; only the grimble-check product path does. Scope: crates/grimble/src/vet_cmd.rs. Reason for no-story: internal gap follow-up of ~EZ00NZ6.
