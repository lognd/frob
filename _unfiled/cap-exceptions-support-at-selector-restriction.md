+++
id = "01M62TNXN0WGJTV9Z56WSK26Q2"
title = "CAP exceptions: support at SELECTOR restriction"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T03:18:56Z"
updated = "2026-11-16T02:05:40Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/check.rs", "crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/model.rs"]

[[acceptance]]
text = "An accept CAP001 atom=ATOM at SELECTOR exception silences only that atom in files matching SELECTOR; other files and atoms still fire"
bound = true
+++

found while working 73YMCSS: accept CAP001 atom=ATOM [at SELECTOR] until=DATE should silence only the atom in the selected files.
