+++
id = "01M4860HNQ80M8GQ4HNF3531D9"
title = "frob doctor warns that gc refused .frob/warm-sweep-stage as outside its roots, though the path is inside .frob"
type = "bug"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-06T08:41:47Z"
updated = "2026-10-06T08:41:47Z"
scope = ["crates/frob-worktree/**"]

[[acceptance]]
text = "frob doctor on a checkout with a warm-sweep stage prints no gc jail warning"
bound = false

[[acceptance]]
text = "a path truly outside the gc roots is still refused (test)"
bound = false
+++

Seen 2026-10-06 on every frob doctor run in the primary checkout: WARN frob_worktree::gc::jail: gc refused a path outside its roots path=.frob/warm-sweep-stage resolved=.frob/warm-sweep-stage. The warm-sweep stage is a detached git worktree frob itself creates under .frob/; either gc's roots must include it (and gc must handle it as a worktree, not a plain directory) or the stage must live where gc expects it. The jail must stay strict for real outside paths.
