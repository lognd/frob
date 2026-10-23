+++
id = "01M5HJNEBY5YBCJB06D5ZSH4H5"
title = "Add TS/JS/C# test vocabulary to testq (WADV010)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:31:46Z"
updated = "2026-10-23T02:23:41Z"
scope = ["crates/grimble-lints/src/testq/**"]

[[acceptance]]
text = "Given a TypeScript or JavaScript test using a known assertion call, when WADV010 runs, then it is classified instead of Unresolved"
bound = false

[[acceptance]]
text = "Given a C# test using a known assertion call, when WADV010 runs, then it is classified instead of Unresolved"
bound = false
+++

Found while working ~DJ4K8YD. testq covers Rust and Python only; other languages report Unresolved.
