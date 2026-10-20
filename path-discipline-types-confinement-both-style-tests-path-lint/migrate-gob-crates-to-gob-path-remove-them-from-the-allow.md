+++
id = "01M41S1MYKQEG5RRJNSKHR84D9"
title = "Migrate gob-* crates to gob-path; remove them from the allow list"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:45Z"
updated = "2026-10-03T20:59:45Z"
scope = ["crates/gob-*/**"]

[[links]]
kind = "blocked-by"
target = "01M41S1KX3ZVF51H8KPJ3YXZF9"

[[acceptance]]
text = "Given the gob-* crates other than gob-path, when clippy runs without their allow-list entries, then it is clean"
bound = false
+++

paths.md migration step 3 for the gob-* crates (gob-path itself excepted).
