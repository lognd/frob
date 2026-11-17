+++
id = "01M65CP8FBE5BKGTBXBYMMQZNY"
title = "LOG: JS non-const fd for fs.writeSync is Unresolved, not resolved"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-11-17T06:07:06Z"
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "Given a let or var bound fd, when fs.writeSync is called with it, then the LOG scan reports it Unresolved"
bound = true
+++

Found while working CS763EX. Fd values from non-const bindings are flagged Unresolved.
