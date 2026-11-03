+++
id = "01M6E374MFD48ESD96CW1YKCKD"
title = "Evaluate PACK001-004, 007, 008 and required-pack semantics in grimble check"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T12:19:47Z"
updated = "2026-11-03T05:56:50Z"
labels = ["no-story"]
scope = ["crates/grimble-check/**"]
+++

Follow-up to ~SZ6F835, which wired only PACK005 and PACK006 (non-required) into grimble check. Remaining: PACK001 lock comparison for local packs (needs a snapshot and grimble.packs.lock writing); PACK002-004, 007, 008 need the full pack loader and external packs; honour required packs (PACK006 required is always false now); packs::load runs twice per check (read_models and collect), share the result; PACK rules in the generated rules index docs if still missing.
