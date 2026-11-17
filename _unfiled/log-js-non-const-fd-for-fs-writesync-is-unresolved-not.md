+++
id = "01M65CP8FBE5BKGTBXBYMMQZNY"
title = "LOG: JS non-const fd for fs.writeSync is Unresolved, not resolved"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-11-17T06:02:10Z"
scope = ["crates/grimble-check/**"]
+++

Found while working CS763EX. Fd values from non-const bindings are flagged Unresolved.
