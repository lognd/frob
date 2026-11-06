+++
id = "01M6R64WYA7HZJC14GQR7JNHZX"
title = "grimble shrink: excuses clause on a kept grant may draw MDL018 on re-bind"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-06T10:23:24Z"
updated = "2026-11-06T10:42:28Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/**"]

[[acceptance]]
text = "grimble shrink --apply output (kept grants) passes grimble check with no MDL018"
bound = true
+++

Found by ~TC6XXY5. shrink writes 'excuses <atom> because=...' after a kept grant; node-level excuses are MDL018 in the spec, so a re-bind may flag it. Verify and either fix the emitted form or the rule. Scope: crates/grimble-bind/**. Reason for no-story: internal follow-up.
