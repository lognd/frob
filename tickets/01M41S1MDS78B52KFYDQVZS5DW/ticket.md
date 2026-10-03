+++
id = "01M41S1MDS78B52KFYDQVZS5DW"
title = "Migrate frob-* crates to gob-path (RelPath, Shown, Arg); remove them from the allow list"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:44Z"
updated = "2026-10-03T20:59:44Z"
scope = ["crates/frob*/**"]

[[links]]
kind = "blocked-by"
target = "01M41S1KX3ZVF51H8KPJ3YXZF9"

[[acceptance]]
text = "Given the frob-* crates, when clippy runs without their allow-list entries, then it is clean"
bound = false
+++

paths.md sections 1 and 3, migration step 3. Replace every path-to-text conversion in the frob-* crates and the frob binary with RelPath, Shown or argv; persisted fields become RelPath. Remove each finished crate from the confinement allow list.
