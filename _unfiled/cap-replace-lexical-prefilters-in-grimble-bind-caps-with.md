+++
id = "01M681KDM0YZZ6T0TJFPCEN1A8"
title = "CAP: replace lexical prefilters in grimble-bind caps with parsed gates for non-C languages"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T03:56:06Z"
updated = "2026-10-31T03:56:06Z"
scope = ["crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "file_is_relevant and mentions_lookup no longer skip function-pointer-only or alias-only files for any language; a computed use with an empty callee does not reach every vocab atom noisily."
bound = false
+++

The lexical file_is_relevant gate was fixed only for c and cpp; other languages still gate on text, which is defeatable. A computed use with an empty callee reaches ALL vocab atoms. (found while working ~S1VG0FG)
