+++
id = "01M65CP8FBE5BKGTBXBYMMQZNY"
title = "LOG: JS non-const fd for fs.writeSync is Unresolved, not resolved"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-10-30T03:12:10Z"
scope = ["crates/grimble-check/**"]
+++

Found while working CS763EX. Fd values from non-const bindings are flagged Unresolved.
