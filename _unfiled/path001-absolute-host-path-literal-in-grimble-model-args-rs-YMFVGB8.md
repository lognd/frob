+++
id = "01M62NX5AXB7N7AZB0DYMFVGB8"
title = "PATH001: absolute host path literal in grimble-model args.rs test"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T01:55:30Z"
updated = "2026-11-09T13:33:36Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/args.rs"]
+++

found while working YCR4M6H: args.rs:317 has a ~other/.ssh/id_rsa literal flagged by PATH001; build it from a root like key_path() in grimble-bind tests
