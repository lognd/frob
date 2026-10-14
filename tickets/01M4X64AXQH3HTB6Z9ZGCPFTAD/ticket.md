+++
id = "01M4X64AXQH3HTB6Z9ZGCPFTAD"
title = "Wire Python type-fact clean-file set into frob-check snapshot graph build"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "Claude"
created = "2026-10-14T12:27:54Z"
updated = "2026-10-14T13:15:33Z"
scope = ["crates/frob-check/**", "docs/reference/tool-stages.md"]

[[acceptance]]
text = "Given [types] trust=checked and a clean file, when the snapshot graph is built, then annotation facts are trusted"
bound = true
+++

Follow-up of 7TYG963: crates/frob-check/src/snapshot.rs must feed the checker's clean-file set into the real graph build so [types] trust applies.
