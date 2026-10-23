+++
id = "01M5NBNPGFD58QQA90YXK87ZP2"
title = "gob-symbols: lib docs still say terms are not cached"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T21:46:32Z"
updated = "2026-10-23T22:58:23Z"
scope = ["crates/gob-symbols/src/lib.rs", "crates/gob-symbols/tests/it/**"]

[[acceptance]]
text = "Given crates/gob-symbols/src/lib.rs, when read, then its docs state that folded terms are cached via grimble-bind CodeFile::folded"
bound = true
+++

Found while working 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E: gob-ir terms and scope graphs now serialize and grimble-bind caches them under grimble-bind/term-v<N>/<adapter identity>; update the lib.rs doc line 46-47.
