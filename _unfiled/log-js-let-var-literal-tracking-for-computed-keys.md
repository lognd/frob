+++
id = "01M65CP8DA9P58X9AJTTMSYTQS"
title = "LOG: JS let/var literal tracking for computed keys"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-11-03T05:56:48Z"
scope = ["crates/grimble-check/**"]
+++

Found while working CS763EX. Only const literals are tracked; let/var reassigned values report Unresolved.
