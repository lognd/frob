+++
id = "01M41S1Q8HEXR5Y9E39EGNECF6"
title = "Migrate grimble-* crates to gob-path; remove them from the allow list"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:47Z"
updated = "2026-10-03T20:59:47Z"
scope = ["crates/grimble*/**"]

[[links]]
kind = "blocked-by"
target = "01M41S1KX3ZVF51H8KPJ3YXZF9"

[[acceptance]]
text = "Given the grimble crates, when clippy runs without their allow-list entries, then it is clean and the allow list holds only gob-path"
bound = false
+++

paths.md migration step 3 for the grimble crates.
