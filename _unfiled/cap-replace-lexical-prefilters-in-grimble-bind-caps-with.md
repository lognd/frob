+++
id = "01M681KDM0YZZ6T0TJFPCEN1A8"
title = "CAP: replace lexical prefilters in grimble-bind caps with parsed gates for non-C languages"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T03:56:06Z"
updated = "2026-11-12T21:28:53Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/Cargo.toml"]

[[acceptance]]
text = "file_is_relevant and mentions_lookup no longer skip function-pointer-only or alias-only files for any language; a computed use with an empty callee does not reach every vocab atom noisily."
bound = true
+++

The lexical file_is_relevant gate was fixed only for c and cpp; other languages still gate on text, which is defeatable. A computed use with an empty callee reaches ALL vocab atoms. (found while working ~S1VG0FG)
