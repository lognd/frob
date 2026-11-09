+++
id = "01M62VRJFC16F47PGR8M0PESCA"
title = "PATH001 absolute host path literal in grimble-model args test"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T03:37:51Z"
updated = "2026-11-09T13:33:36Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/args.rs"]
+++

found while working ~1X6RRD6: args.rs:317 test uses a literal absolute path, flagged PATH001.
