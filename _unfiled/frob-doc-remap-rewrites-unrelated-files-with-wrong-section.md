+++
id = "01M6Q6M5H5N0SAS5EK2TY5XYRE"
title = "frob doc remap rewrites unrelated files with wrong section numbers and unbalanced backticks"
type = "bug"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-06T01:12:30Z"
updated = "2026-11-06T01:12:30Z"
labels = ["no-story"]
+++

Found landing ABW7H0Q: a real doc remap run rewrote 64 unrelated files with wrong section numbers and unbalanced backticks; reverted and patched by hand. Also refused 3 MOVED.toml rows with stale anchors. no-story: internal docs tooling defect with no standalone user-visible story.
